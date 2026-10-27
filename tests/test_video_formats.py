from __future__ import annotations

import io
import json
import subprocess
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

import app as app_module
from converter import VIDEO_OUTPUT_FORMATS


class VideoFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.previous_jobs_dir = app_module.JOBS_DIR
        app_module.JOBS_DIR = cls.root / "jobs"
        app_module.JOBS_DIR.mkdir()
        app_module.app.config.update(TESTING=True)
        cls.client = app_module.app.test_client()
        source = cls.root / "source.mp4"
        cls.run_ffmpeg([
            "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=523:sample_rate=44100",
            "-t", "0.6", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ac", "2", str(source),
        ])
        cls.videos = {}
        for output_format, (video_codec, audio_codec, extension) in VIDEO_OUTPUT_FORMATS.items():
            path = cls.root / f"sample_{output_format}{extension}"
            options = {
                "hevc": ["-tag:v", "hvc1", "-x265-params", "log-level=error"],
                "webm": ["-ar", "48000", "-deadline", "realtime", "-cpu-used", "8"],
                "mpeg": ["-r", "30", "-ar", "48000"],
            }.get(output_format, [])
            cls.run_ffmpeg([
                "-i", str(source), "-c:v", video_codec, "-c:a", audio_codec,
                *options, str(path),
            ])
            cls.videos[output_format] = path.read_bytes()
        silent = cls.root / "silent.mp4"
        cls.run_ffmpeg(["-i", str(source), "-an", "-c:v", "copy", str(silent)])
        cls.silent = silent.read_bytes()
        odd = cls.root / "odd.mov"
        cls.run_ffmpeg([
            "-f", "lavfi", "-i", "testsrc=size=161x121:rate=30", "-t", "0.6",
            "-c:v", "png", str(odd),
        ])
        cls.odd = odd.read_bytes()
        iphone = cls.root / "iphone.mov"
        cls.run_ffmpeg([
            "-i", str(source), "-c:v", "libx265", "-pix_fmt", "yuv420p10le",
            "-tag:v", "hvc1", "-x265-params", "log-level=error", "-c:a", "copy", str(iphone),
        ])
        rotated = cls.root / "iphone_portrait.mov"
        cls.run_ffmpeg([
            "-display_rotation", "90", "-i", str(iphone), "-c", "copy", str(rotated),
        ])
        cls.iphone = rotated.read_bytes()
        vp9_mkv = cls.root / "vp9.mkv"
        cls.run_ffmpeg(["-i", str(cls.root / "sample_webm.webm"), "-c", "copy", str(vp9_mkv)])
        cls.vp9_mkv = vp9_mkv.read_bytes()
        audio_only = cls.root / "audio.m4a"
        cls.run_ffmpeg(["-i", str(source), "-vn", "-c:a", "copy", str(audio_only)])
        cls.audio_only = audio_only.read_bytes()

    @staticmethod
    def run_ffmpeg(arguments):
        return subprocess.run(
            ["ffmpeg", "-v", "error", *arguments], check=True, capture_output=True,
        )

    @classmethod
    def tearDownClass(cls):
        app_module.JOBS_DIR = cls.previous_jobs_dir
        cls.temp.cleanup()

    def upload(self, files):
        response = self.client.post(
            "/api/upload",
            data={"category": "video", "files": [(io.BytesIO(data), name) for data, name in files]},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()

    def request_conversion(self, upload, output_format):
        return self.client.post("/api/convert", json={
            "job_id": upload["job_id"], "mode": "convert_format",
            "file_ids": [item["id"] for item in upload["files"]],
            "options": {"format": output_format},
        })

    def convert(self, upload, output_format):
        response = self.request_conversion(upload, output_format)
        self.assertEqual(response.status_code, 202, response.get_data(as_text=True))
        deadline = time.monotonic() + 45
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
        self.fail("Video conversion timed out")

    def assert_playable_video(self, data, output_format, *, audio=True, size=(160, 120)):
        path = self.root / f"output{VIDEO_OUTPUT_FORMATS[output_format][2]}"
        path.write_bytes(data)
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-count_frames", "-show_entries",
                "format=format_name,duration:format_tags=major_brand:"
                "stream=codec_type,codec_name,codec_tag_string,width,height,nb_read_frames,avg_frame_rate",
                "-of", "json", str(path),
            ],
            check=True, capture_output=True, text=True,
        )
        info = json.loads(probe.stdout)
        videos = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
        audios = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
        self.assertEqual(len(videos), 1)
        self.assertEqual(len(audios), 1 if audio else 0)
        video = videos[0]
        self.assertEqual((video["width"], video["height"]), size)
        self.assertGreaterEqual(int(video["nb_read_frames"]), 15)
        expected_codec = {"mp4": "h264", "hevc": "hevc", "mov": "h264", "avi": "mpeg4",
                          "mkv": "h264", "webm": "vp9", "mpeg": "mpeg2video"}[output_format]
        self.assertEqual(video["codec_name"], expected_codec)
        if output_format == "hevc":
            self.assertEqual(video["codec_tag_string"], "hvc1")
        if output_format == "mpeg":
            self.assertEqual(video["avg_frame_rate"], "30/1")
        if audio:
            expected_audio = {"avi": "mp3", "webm": "opus", "mpeg": "mp2"}.get(output_format, "aac")
            self.assertEqual(audios[0]["codec_name"], expected_audio)
        expected_container = {"hevc": "mp4", "mkv": "matroska"}.get(output_format, output_format)
        self.assertIn(expected_container, info["format"]["format_name"].split(","))
        if output_format in {"mp4", "mov", "hevc"}:
            brand = info["format"]["tags"]["major_brand"].strip()
            self.assertEqual(brand == "qt", output_format == "mov")
        self.assertGreaterEqual(float(info["format"]["duration"]), 0.45)
        self.assertLess(float(info["format"]["duration"]), 1.0)
        self.run_ffmpeg(["-xerror", "-i", str(path), "-f", "null", "-"])

    def test_all_seven_output_formats_can_convert_to_each_other(self):
        for source_format, source_bytes in self.videos.items():
            extension = VIDEO_OUTPUT_FORMATS[source_format][2]
            upload = self.upload([(source_bytes, f"clip{extension}")])
            self.assertEqual(upload["files"][0]["format"], source_format)
            for output_format, (_, _, extension) in VIDEO_OUTPUT_FORMATS.items():
                if output_format == source_format:
                    continue
                with self.subTest(source=source_format, output=output_format):
                    data, name = self.convert(upload, output_format)
                    self.assertEqual(name, f"clip{extension}")
                    self.assert_playable_video(data, output_format)

    def test_same_format_and_aliases_are_rejected_before_starting_conversion(self):
        for source_format, source_bytes in self.videos.items():
            extension = VIDEO_OUTPUT_FORMATS[source_format][2]
            aliases = {"mp4": ("mp4", "m4v"), "hevc": ("hevc", "h265", "h.265"),
                       "mpeg": ("mpeg", "mpg")}.get(source_format, (source_format,))
            upload = self.upload([(source_bytes, f"clip{extension.upper()}")])
            for alias in aliases:
                with self.subTest(source=source_format, output=alias):
                    response = self.request_conversion(upload, alias.upper())
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("請選擇其他輸出格式", response.get_json()["error"])
                    status = self.client.get(f"/api/jobs/{upload['job_id']}/status").get_json()
                    self.assertEqual(status["status"], "idle")

    def test_upload_and_output_aliases_are_supported(self):
        for source_format, alias in (("mp4", "M4V"), ("mpeg", "MPG")):
            with self.subTest(source=alias):
                upload = self.upload([(self.videos[source_format], f"clip.{alias}")])
                self.assertEqual(upload["files"][0]["format"], source_format)
        upload = self.upload([(self.videos["mov"], "clip.mov")])
        for alias, canonical in (("M4V", "mp4"), ("MPG", "mpeg"), ("H.265", "hevc")):
            with self.subTest(output=alias):
                data, name = self.convert(upload, alias)
                self.assertTrue(name.endswith(VIDEO_OUTPUT_FORMATS[canonical][2]))
                self.assert_playable_video(data, canonical)

    def test_mixed_batch_rejects_a_format_present_in_any_file(self):
        upload = self.upload([(self.videos["mp4"], "first.mp4"), (self.videos["mov"], "second.mov")])
        response = self.request_conversion(upload, "mov")
        self.assertEqual(response.status_code, 400)
        self.assertIn("second.mov", response.get_json()["error"])

    def test_batch_outputs_follow_requested_order_and_keep_duplicate_stems(self):
        upload = self.upload([
            (self.videos["mp4"], "clip.mp4"), (self.videos["mov"], "other.mov"),
            (self.videos["avi"], "clip.avi"),
        ])
        upload["files"].reverse()
        data, name = self.convert(upload, "mkv")
        self.assertEqual(name, "converted_videos.zip")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.namelist(), ["clip.mkv", "other.mkv", "clip_2.mkv"])
            for filename in archive.namelist():
                self.assert_playable_video(archive.read(filename), "mkv")

    def test_actual_content_distinguishes_mov_mp4_mkv_and_webm(self):
        for source_format, filename, output_format in (
            ("mov", "renamed.mp4", "mp4"), ("mp4", "renamed.mov", "mov"),
            ("webm", "renamed.mkv", "mkv"), ("mkv", "renamed.webm", "webm"),
        ):
            with self.subTest(source=source_format):
                upload = self.upload([(self.videos[source_format], filename)])
                self.assertEqual(upload["files"][0]["format"], source_format)
                self.assertEqual(self.request_conversion(upload, source_format).status_code, 400)
                data, _ = self.convert(upload, output_format)
                self.assert_playable_video(data, output_format)

    def test_vp9_in_matroska_is_not_mistaken_for_webm(self):
        upload = self.upload([(self.vp9_mkv, "renamed.webm")])
        self.assertEqual(upload["files"][0]["format"], "mkv")
        self.assertEqual(self.request_conversion(upload, "mkv").status_code, 400)
        data, _ = self.convert(upload, "webm")
        self.assert_playable_video(data, "webm")

    def test_silent_videos_can_convert_to_every_other_format(self):
        upload = self.upload([(self.silent, "silent.mp4")])
        for output_format in VIDEO_OUTPUT_FORMATS:
            if output_format == "mp4":
                continue
            with self.subTest(output=output_format):
                data, _ = self.convert(upload, output_format)
                self.assert_playable_video(data, output_format, audio=False)

    def test_odd_dimensions_are_padded_instead_of_cropped(self):
        upload = self.upload([(self.odd, "odd.mov")])
        for output_format in VIDEO_OUTPUT_FORMATS:
            if output_format == "mov":
                continue
            with self.subTest(output=output_format):
                data, _ = self.convert(upload, output_format)
                self.assert_playable_video(data, output_format, audio=False, size=(162, 122))

    def test_iphone_10_bit_hevc_mov_retains_portrait_orientation(self):
        upload = self.upload([(self.iphone, "IMG_0001.MOV")])
        self.assertEqual(upload["files"][0]["format"], "mov")
        for output_format in ("mp4", "hevc"):
            with self.subTest(output=output_format):
                data, name = self.convert(upload, output_format)
                self.assertEqual(name, "IMG_0001.mp4")
                self.assert_playable_video(data, output_format, size=(120, 160))

    def test_invalid_output_formats_are_rejected(self):
        upload = self.upload([(self.videos["mp4"], "clip.mp4")])
        for invalid in ("mp3", "../../output", ["mov"], {"format": "mov"}, None):
            with self.subTest(format=invalid):
                self.assertEqual(self.request_conversion(upload, invalid).status_code, 400)

    def test_corrupt_files_and_audio_only_files_are_rejected_on_upload(self):
        for content in (b"invalid video", self.audio_only):
            with self.subTest(audio_only=content == self.audio_only):
                response = self.client.post(
                    "/api/upload", data={"category": "video", "files": (io.BytesIO(content), "broken.mp4")},
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("無法辨識影片格式", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
