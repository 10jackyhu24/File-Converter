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
from converter import AUDIO_OUTPUT_FORMATS


class AudioFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.previous_jobs_dir = app_module.JOBS_DIR
        app_module.JOBS_DIR = cls.root / "jobs"
        app_module.JOBS_DIR.mkdir()
        app_module.app.config.update(TESTING=True)
        cls.client = app_module.app.test_client()
        cls.audio = {}
        source = cls.root / "source.wav"
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                "sine=frequency=523:sample_rate=44100", "-t", "0.6", "-ac", "2", str(source),
            ],
            check=True, capture_output=True,
        )
        for output_format, (codec, extension) in AUDIO_OUTPUT_FORMATS.items():
            path = cls.root / f"sample{extension}"
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-i", str(source), "-c:a", codec,
                    *(["-ar", "48000"] if output_format == "opus" else []), str(path),
                ],
                check=True, capture_output=True,
            )
            cls.audio[output_format] = path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        app_module.JOBS_DIR = cls.previous_jobs_dir
        cls.temp.cleanup()

    def upload(self, files):
        response = self.client.post(
            "/api/upload",
            data={"category": "audio", "files": [(io.BytesIO(data), name) for data, name in files]},
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
        self.fail("Audio conversion timed out")

    def assert_playable_audio(self, data, output_format):
        path = self.root / f"output{AUDIO_OUTPUT_FORMATS[output_format][1]}"
        path.write_bytes(data)
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=format_name,duration:stream=codec_type,codec_name,channels,sample_rate",
                "-of", "json", str(path),
            ],
            check=True, capture_output=True, text=True,
        )
        info = json.loads(probe.stdout)
        self.assertEqual(len(info["streams"]), 1)
        stream = info["streams"][0]
        self.assertEqual(stream["codec_type"], "audio")
        self.assertEqual(stream["channels"], 2)
        expected_codec = {"mp3": "mp3", "wav": "pcm_s16le", "m4a": "aac", "aac": "aac",
                          "ogg": "vorbis", "flac": "flac", "opus": "opus"}[output_format]
        self.assertEqual(stream["codec_name"], expected_codec)
        expected_container = {"m4a": "m4a", "opus": "ogg"}.get(output_format, output_format)
        self.assertIn(expected_container, info["format"]["format_name"].split(","))
        self.assertGreater(float(info["format"]["duration"]), 0.5)
        self.assertLess(float(info["format"]["duration"]), 1.0)
        if output_format == "opus":
            self.assertEqual(stream["sample_rate"], "48000")
        decoded = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "pipe:1"],
            check=True, capture_output=True,
        )
        self.assertGreater(len(decoded.stdout), 40_000)
        self.assertNotEqual(set(decoded.stdout), {0})

    def test_all_seven_formats_can_convert_to_each_other(self):
        for source_format, source_bytes in self.audio.items():
            upload = self.upload([(source_bytes, f"tone{AUDIO_OUTPUT_FORMATS[source_format][1]}")])
            self.assertEqual(upload["files"][0]["format"], source_format)
            for output_format, (_, extension) in AUDIO_OUTPUT_FORMATS.items():
                if source_format == output_format:
                    continue
                with self.subTest(source=source_format, output=output_format):
                    data, name = self.convert(upload, output_format)
                    self.assertEqual(name, f"tone{extension}")
                    self.assert_playable_audio(data, output_format)

    def test_same_format_is_rejected_before_starting_conversion(self):
        for source_format, source_bytes in self.audio.items():
            with self.subTest(format=source_format):
                upload = self.upload([(source_bytes, f"tone.{source_format.upper()}")])
                response = self.request_conversion(upload, source_format.upper())
                self.assertEqual(response.status_code, 400)
                self.assertIn("請選擇其他輸出格式", response.get_json()["error"])
                status = self.client.get(f"/api/jobs/{upload['job_id']}/status").get_json()
                self.assertEqual(status["status"], "idle")

    def test_batch_rejects_a_format_present_in_any_file(self):
        upload = self.upload([(self.audio["wav"], "first.wav"), (self.audio["mp3"], "second.mp3")])
        response = self.request_conversion(upload, "mp3")
        self.assertEqual(response.status_code, 400)
        self.assertIn("second.mp3", response.get_json()["error"])

    def test_batch_outputs_are_zipped_in_requested_order_with_unique_names(self):
        upload = self.upload([(self.audio["wav"], "tone.wav"), (self.audio["mp3"], "tone.mp3")])
        upload["files"].reverse()
        data, name = self.convert(upload, "flac")
        self.assertEqual(name, "converted_audio.zip")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(archive.namelist(), ["tone.flac", "tone_2.flac"])
            for filename in archive.namelist():
                self.assert_playable_audio(archive.read(filename), "flac")

    def test_format_detection_uses_content_instead_of_filename(self):
        upload = self.upload([(self.audio["wav"], "renamed.mp3")])
        self.assertEqual(upload["files"][0]["format"], "wav")
        self.assertEqual(self.request_conversion(upload, "wav").status_code, 400)
        data, name = self.convert(upload, "MP3")
        self.assertEqual(name, "renamed.mp3")
        self.assert_playable_audio(data, "mp3")

    def test_opus_in_ogg_container_is_identified_as_opus(self):
        upload = self.upload([(self.audio["opus"], "speech.ogg")])
        self.assertEqual(upload["files"][0]["format"], "opus")
        self.assertEqual(self.request_conversion(upload, "opus").status_code, 400)
        data, _ = self.convert(upload, "ogg")
        self.assert_playable_audio(data, "ogg")

    def test_invalid_output_formats_are_rejected(self):
        upload = self.upload([(self.audio["wav"], "tone.wav")])
        for invalid in ("mp4", "../../output", ["mp3"], {"format": "mp3"}, None):
            with self.subTest(format=invalid):
                response = self.request_conversion(upload, invalid)
                self.assertEqual(response.status_code, 400)

    def test_invalid_audio_is_rejected_on_upload(self):
        response = self.client.post(
            "/api/upload", data={"category": "audio", "files": (io.BytesIO(b"invalid audio"), "broken.mp3")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("無法辨識音檔格式", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
