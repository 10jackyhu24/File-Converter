from __future__ import annotations

import io
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import fitz
from PIL import Image

import app as app_module
from converter import IMAGE_OUTPUT_FORMATS


class ImageFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.previous_jobs_dir = app_module.JOBS_DIR
        app_module.JOBS_DIR = Path(cls.temp.name)
        app_module.app.config.update(TESTING=True)
        cls.client = app_module.app.test_client()
        cls.images = {}
        for key, (pillow_format, _) in IMAGE_OUTPUT_FORMATS.items():
            output = io.BytesIO()
            with Image.new("RGB", (64, 48), "#326eab") as image:
                image.save(output, pillow_format)
            cls.images[key] = output.getvalue()
        frames = [Image.new("RGBA", (64, 48), color) for color in ("red", "green", "blue")]
        output = io.BytesIO()
        try:
            frames[0].save(output, "GIF", save_all=True, append_images=frames[1:], duration=[60, 130, 230], loop=2)
            cls.animated_gif = output.getvalue()
        finally:
            for frame in frames:
                frame.close()

    @classmethod
    def tearDownClass(cls):
        app_module.JOBS_DIR = cls.previous_jobs_dir
        cls.temp.cleanup()

    def upload(self, files):
        response = self.client.post(
            "/api/upload",
            data={"category": "image", "files": [(io.BytesIO(data), name) for data, name in files]},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()

    def convert(self, upload, mode, options=None):
        response = self.client.post(
            "/api/convert",
            json={
                "job_id": upload["job_id"], "mode": mode,
                "file_ids": [item["id"] for item in upload["files"]], "options": options or {},
            },
        )
        self.assertEqual(response.status_code, 202, response.get_data(as_text=True))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status = self.client.get(response.get_json()["status_url"]).get_json()
            if status["status"] == "failed":
                self.fail(status["error"])
            if status["status"] == "completed":
                self.assertEqual(status["progress"], 100)
                download = self.client.get(status["download_url"])
                try:
                    self.assertEqual(download.status_code, 200)
                    return download.get_data(), status["filename"]
                finally:
                    download.close()
            time.sleep(0.01)
        self.fail("Image conversion timed out")

    def test_all_seven_formats_can_convert_to_each_other(self):
        for source_format, source_bytes in self.images.items():
            extension = IMAGE_OUTPUT_FORMATS[source_format][1]
            upload = self.upload([(source_bytes, f"photo{extension}")])
            for output_format, (pillow_format, output_extension) in IMAGE_OUTPUT_FORMATS.items():
                if output_format == source_format:
                    continue
                with self.subTest(source=source_format, output=output_format):
                    data, name = self.convert(upload, "convert_format", {"format": output_format})
                    self.assertTrue(name.endswith(output_extension), name)
                    with Image.open(io.BytesIO(data)) as image:
                        image.load()
                        self.assertEqual(image.format, pillow_format)
                        self.assertEqual(image.size, (64, 48))

    def test_upload_accepts_more_than_1000_images(self):
        upload = self.upload([(self.images["png"], f"photo_{index:04d}.png") for index in range(1001)])
        self.assertEqual(len(upload["files"]), 1001)

    def test_upload_still_enforces_request_size_limit(self):
        self.assertEqual(app_module.app.config["MAX_CONTENT_LENGTH"], 2 * 1024 * 1024 * 1024)
        with patch.dict(app_module.app.config, {"MAX_CONTENT_LENGTH": 1024}):
            response = self.client.post(
                "/api/upload",
                data={"category": "image", "files": [(io.BytesIO(self.images["png"]), f"photo_{index}.png") for index in range(20)]},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 413)

    def test_many_images_become_one_animated_gif_without_merging_identical_frames(self):
        upload = self.upload([(self.images["png"], f"frame_{index:03d}.png") for index in range(65)])
        data, name = self.convert(upload, "convert_format", {"format": "gif"})
        self.assertTrue(name.endswith(".gif"))
        self.assertTrue(data.startswith(b"GIF89a"))
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.n_frames, 65)
            self.assertEqual(image.info["loop"], 0)
            image.seek(64)
            image.load()
            self.assertEqual(image.info["duration"], 100)
            self.assertEqual(image.convert("RGB").getpixel((0, 0)), (50, 110, 171))

    def test_gif_combines_mixed_formats_in_requested_order_and_centers_each_image(self):
        inputs = []
        for name, size, color, fmt in (
            ("red.png", (64, 48), "red", "PNG"),
            ("green.jpg", (32, 24), "green", "JPEG"),
            ("blue.heic", (80, 30), "blue", "HEIF"),
        ):
            buffer = io.BytesIO()
            with Image.new("RGB", size, color) as image:
                image.save(buffer, fmt)
            inputs.append((buffer.getvalue(), name))
        upload = self.upload(inputs)
        upload["files"].reverse()
        data, name = self.convert(upload, "convert_format", {"format": "gif"})
        self.assertTrue(name.endswith(".gif"))
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (80, 48))
            self.assertEqual(image.n_frames, 3)
            for index, expected in enumerate(((0, 0, 255), (0, 128, 0), (255, 0, 0))):
                image.seek(index)
                with image.convert("RGBA") as frame:
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    actual = frame.getpixel((40, 24))[:3]
                    self.assertTrue(all(abs(a - b) <= 20 for a, b in zip(actual, expected)), (actual, expected))

    def test_multiple_gifs_can_be_joined_and_keep_each_frame_duration(self):
        upload = self.upload([(self.animated_gif, "animated.gif"), (self.images["gif"], "still.gif")])
        data, name = self.convert(upload, "convert_format", {"format": "gif"})
        self.assertTrue(name.endswith(".gif"))
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.n_frames, 4)
            self.assertEqual(image.info["loop"], 0)
            durations = []
            for index in range(4):
                image.seek(index)
                image.load()
                durations.append(image.info["duration"])
            self.assertEqual(durations, [60, 130, 230, 100])

    def test_gif_fps_overrides_source_frame_timing(self):
        upload = self.upload([(self.animated_gif, "animated.gif"), (self.images["png"], "still.png")])
        data, _ = self.convert(upload, "convert_format", {"format": "gif", "fps": 5})
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.n_frames, 4)
            for index in range(image.n_frames):
                image.seek(index)
                image.load()
                self.assertEqual(image.info["duration"], 200)

    def test_gif_fps_rounding_preserves_average_frame_rate(self):
        upload = self.upload([(self.images["png"], f"frame_{index:03d}.png") for index in range(60)])
        for fps in (1, 24, 30, 60):
            with self.subTest(fps=fps):
                data, _ = self.convert(upload, "convert_format", {"format": "gif", "fps": fps})
                with Image.open(io.BytesIO(data)) as image:
                    self.assertEqual(image.n_frames, 60)
                    total_ms = 0
                    for index in range(image.n_frames):
                        image.seek(index)
                        image.load()
                        duration = image.info["duration"]
                        self.assertGreaterEqual(duration, 10)
                        self.assertLessEqual(abs(duration - 1000 / fps), 10)
                        total_ms += duration
                    self.assertEqual(total_ms, 60 * 1000 / fps)

    def test_invalid_gif_fps_is_rejected(self):
        upload = self.upload([(self.images["png"], "photo.png")])
        for fps in (0, -1, 61, 1.5, "fast", None, True, [], {}):
            with self.subTest(fps=fps):
                response = self.client.post("/api/convert", json={
                    "job_id": upload["job_id"], "mode": "convert_format",
                    "file_ids": [upload["files"][0]["id"]], "options": {"format": "gif", "fps": fps},
                })
                self.assertEqual(response.status_code, 400)

    def test_fps_setting_does_not_affect_other_formats(self):
        upload = self.upload([(self.images["png"], "photo.png")])
        data, _ = self.convert(upload, "convert_format", {"format": "jpeg", "fps": "unused"})
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.format, "JPEG")

    def test_heic_input_in_existing_image_modes(self):
        upload = self.upload([(self.images["heic"], "phone.HEIC")])
        for mode, options, expected_format in (
            ("compress", {"target_mb": 0.1}, "JPEG"),
            ("noise", {"ratio": 5}, "PNG"),
            ("blur", {"pixels": 2}, "PNG"),
            ("to_pdf", {}, "PDF"),
        ):
            with self.subTest(mode=mode):
                data, _ = self.convert(upload, mode, options)
                if expected_format == "PDF":
                    with fitz.open(stream=data, filetype="pdf") as document:
                        self.assertEqual(document.page_count, 1)
                else:
                    with Image.open(io.BytesIO(data)) as image:
                        image.load()
                        self.assertEqual(image.format, expected_format)

    def test_heif_extensions_and_browser_preview(self):
        for extension in ("HEIC", "heif", "hif"):
            with self.subTest(extension=extension):
                upload = self.upload([(self.images["heic"], f"phone.{extension}")])
                self.assertEqual(upload["files"][0]["format"], "heic")
                file_id = upload["files"][0]["id"]
                response = self.client.get(f"/api/jobs/{upload['job_id']}/files/{file_id}/preview")
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.mimetype, "image/jpeg")
                    with Image.open(io.BytesIO(response.get_data())) as preview:
                        preview.load()
                        self.assertEqual(preview.size, (64, 48))
                finally:
                    response.close()

    def test_batch_conversion_keeps_duplicate_stems(self):
        upload = self.upload([(self.images["png"], "photo.png"), (self.images["jpeg"], "photo.jpg")])
        data, name = self.convert(upload, "convert_format", {"format": "webp"})
        self.assertTrue(name.endswith(".zip"))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.namelist(), ["photo.webp", "photo_2.webp"])
            for filename in archive.namelist():
                with Image.open(io.BytesIO(archive.read(filename))) as image:
                    image.load()
                    self.assertEqual(image.format, "WEBP")

    def test_animation_and_timing_are_preserved(self):
        upload = self.upload([(self.animated_gif, "animated.gif")])
        for output_format in ("webp", "gif"):
            with self.subTest(output=output_format):
                data, _ = self.convert(upload, "convert_format", {"format": output_format})
                with Image.open(io.BytesIO(data)) as image:
                    self.assertEqual(image.n_frames, 3)
                    self.assertEqual(image.info["loop"], 2)
                    durations = []
                    for index in range(image.n_frames):
                        image.seek(index)
                        image.load()
                        durations.append(image.info["duration"])
                    self.assertEqual(durations, [60, 130, 230])
                upload = self.upload([(data, "animated.webp")])

    def test_gif_exports_every_frame_to_each_static_format(self):
        upload = self.upload([(self.animated_gif, "animated.gif")])
        colors = [(255, 0, 0), (0, 128, 0), (0, 0, 255)]
        for output_format in ("png", "jpeg", "heic", "bmp", "tiff"):
            with self.subTest(output=output_format):
                data, name = self.convert(upload, "convert_format", {"format": output_format})
                self.assertTrue(name.endswith(".zip"))
                pillow_format, extension = IMAGE_OUTPUT_FORMATS[output_format]
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    self.assertEqual(archive.namelist(), [f"animated_frame_{index:04d}{extension}" for index in (1, 2, 3)])
                    for filename, expected in zip(archive.namelist(), colors):
                        with Image.open(io.BytesIO(archive.read(filename))) as image:
                            image.load()
                            self.assertEqual(image.format, pillow_format)
                            self.assertEqual(image.size, (64, 48))
                            actual = image.convert("RGB").getpixel((0, 0))
                            self.assertTrue(all(abs(a - b) <= 20 for a, b in zip(actual, expected)), (actual, expected))

    def test_gif_frame_names_do_not_overwrite_other_files(self):
        upload = self.upload([
            (self.animated_gif, "animated.gif"),
            (self.images["png"], "animated_frame_0001.png"),
        ])
        data, _ = self.convert(upload, "convert_format", {"format": "jpeg"})
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.namelist(), [
                "animated_frame_0001.jpg", "animated_frame_0002.jpg", "animated_frame_0003.jpg",
                "animated_frame_0001_2.jpg",
            ])

    def test_transparency_and_white_background(self):
        output = io.BytesIO()
        with Image.new("RGBA", (64, 48), (255, 0, 0, 0)) as image:
            image.putpixel((32, 24), (0, 255, 0, 255))
            image.save(output, "PNG")
        upload = self.upload([(output.getvalue(), "transparent.png")])
        for output_format in IMAGE_OUTPUT_FORMATS:
            if output_format == "png":
                continue
            with self.subTest(output=output_format):
                data, _ = self.convert(upload, "convert_format", {"format": output_format})
                with Image.open(io.BytesIO(data)) as image:
                    if output_format in {"jpeg", "bmp"}:
                        self.assertTrue(all(value >= 250 for value in image.convert("RGB").getpixel((0, 0))))
                    else:
                        self.assertEqual(image.convert("RGBA").getpixel((0, 0))[3], 0)

    def test_exif_orientation_is_applied(self):
        output = io.BytesIO()
        with Image.new("RGB", (64, 48), "red") as image:
            exif = Image.Exif()
            exif[274] = 6
            image.save(output, "JPEG", exif=exif)
        upload = self.upload([(output.getvalue(), "rotated.jpg")])
        for output_format in ("png", "heic", "gif"):
            with self.subTest(output=output_format):
                data, _ = self.convert(upload, "convert_format", {"format": output_format})
                with Image.open(io.BytesIO(data)) as image:
                    self.assertEqual(image.size, (48, 64))
                    self.assertNotIn(274, image.getexif())

    def test_same_format_and_aliases_are_rejected(self):
        for source_format, source_bytes in self.images.items():
            aliases = {"jpeg": ("jpeg", "jpg", "JPG"), "heic": ("heic", "heif"), "tiff": ("tiff", "tif")}
            upload = self.upload([(source_bytes, "photo" + IMAGE_OUTPUT_FORMATS[source_format][1])])
            for alias in aliases.get(source_format, (source_format,)):
                with self.subTest(source=source_format, target=alias):
                    response = self.client.post("/api/convert", json={
                        "job_id": upload["job_id"], "mode": "convert_format",
                        "file_ids": [upload["files"][0]["id"]], "options": {"format": alias},
                    })
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("請選擇其他輸出格式", response.get_json()["error"])
                    status = self.client.get(f"/api/jobs/{upload['job_id']}/status").get_json()
                    self.assertEqual(status["status"], "idle")

    def test_mixed_batch_rejects_a_format_present_in_any_file(self):
        upload = self.upload([(self.images["png"], "first.png"), (self.images["jpeg"], "second.jpg")])
        response = self.client.post("/api/convert", json={
            "job_id": upload["job_id"], "mode": "convert_format",
            "file_ids": [item["id"] for item in upload["files"]], "options": {"format": "jpeg"},
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("second.jpg", response.get_json()["error"])

    def test_same_format_uses_actual_content_instead_of_filename(self):
        upload = self.upload([(self.images["png"], "renamed.jpg")])
        self.assertEqual(upload["files"][0]["format"], "png")
        response = self.client.post("/api/convert", json={
            "job_id": upload["job_id"], "mode": "convert_format",
            "file_ids": [upload["files"][0]["id"]], "options": {"format": "png"},
        })
        self.assertEqual(response.status_code, 400)
        data, _ = self.convert(upload, "convert_format", {"format": "jpeg"})
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.format, "JPEG")

    def test_invalid_output_format_is_rejected(self):
        upload = self.upload([(self.images["png"], "photo.png")])
        for invalid in ("svg", "../../output", ["png"], {"format": "png"}, None):
            with self.subTest(format=invalid):
                response = self.client.post("/api/convert", json={
                    "job_id": upload["job_id"], "mode": "convert_format",
                    "file_ids": [upload["files"][0]["id"]], "options": {"format": invalid},
                })
                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
