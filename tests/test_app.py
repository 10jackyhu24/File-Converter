from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import app as app_module


class FileConverterSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        app_module.JOBS_DIR = cls.root / "jobs"
        app_module.JOBS_DIR.mkdir()
        app_module.app.config.update(TESTING=True)
        cls.client = app_module.app.test_client()

        cls.image_bytes = cls.make_image("#e27752")
        cls.image_bytes_2 = cls.make_image("#1d7b83")
        cls.pdf_bytes = cls.make_pdf("#e27752")
        cls.pdf_bytes_2 = cls.make_pdf("#1d7b83")

        cls.media_dir = cls.root / "media"
        cls.media_dir.mkdir()
        cls.video_path = cls.media_dir / "sample.mp4"
        cls.audio_path = cls.media_dir / "sample.wav"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=8",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "1.2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.video_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=523:sample_rate=44100",
                "-t", "1", str(cls.audio_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def make_image(color: str) -> bytes:
        output = io.BytesIO()
        Image.new("RGB", (160, 100), color).save(output, "PNG")
        return output.getvalue()

    @staticmethod
    def make_pdf(color: str) -> bytes:
        output = io.BytesIO()
        Image.new("RGB", (160, 100), color).save(output, "PDF")
        return output.getvalue()

    def upload(self, category: str, files: list[tuple[bytes, str]]):
        response = self.client.post(
            "/api/upload",
            data={"category": category, "files": [(io.BytesIO(data), name) for data, name in files]},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        return payload

    def convert(self, upload: dict, mode: str, options: dict | None = None):
        response = self.client.post(
            "/api/convert",
            json={
                "job_id": upload["job_id"],
                "mode": mode,
                "file_ids": [item["id"] for item in upload["files"]],
                "options": options or {},
            },
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        download = self.client.get(payload["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertGreater(len(download.get_data()), 10)
        download.close()
        return payload

    def test_index_and_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertTrue(self.client.get("/api/health").get_json()["ok"])

    def test_all_image_modes(self):
        upload = self.upload("image", [(self.image_bytes, "one.png"), (self.image_bytes_2, "two.png")])
        self.convert(upload, "compress", {"target_mb": 1})
        self.convert(upload, "to_pdf")
        self.convert(upload, "noise", {"ratio": 10})
        self.convert(upload, "blur", {"pixels": 3})

    def test_all_pdf_modes(self):
        upload = self.upload("pdf", [(self.pdf_bytes, "one.pdf"), (self.pdf_bytes_2, "two.pdf")])
        self.convert(upload, "merge")
        self.convert(upload, "to_images")

    def test_audio_volume(self):
        upload = self.upload("audio", [(self.audio_path.read_bytes(), "tone.wav")])
        self.convert(upload, "volume", {"db": 2.5})

    def test_all_video_modes(self):
        upload = self.upload("video", [(self.video_path.read_bytes(), "clip.mp4")])
        self.convert(upload, "compress", {"target_mb": 1})
        self.convert(upload, "extract_frames")
        self.convert(upload, "extract_audio", {"bitrate": 64})

    def test_rejects_wrong_extension(self):
        response = self.client.post(
            "/api/upload",
            data={"category": "pdf", "files": (io.BytesIO(self.image_bytes), "not-a-pdf.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
