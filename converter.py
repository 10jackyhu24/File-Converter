from __future__ import annotations

import math
import os
import shutil
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFilter, ImageOps
from pypdf import PdfReader, PdfWriter


class ConversionError(RuntimeError):
    """A conversion error that is safe to show in the UI."""


def _safe_stem(name: str) -> str:
    stem = Path(name).stem.strip().replace(" ", "_")
    return "".join(c for c in stem if c.isalnum() or c in "_-.")[:80] or "file"


def _unique_path(folder: Path, name: str) -> Path:
    target = folder / name
    index = 2
    while target.exists():
        target = folder / f"{Path(name).stem}_{index}{Path(name).suffix}"
        index += 1
    return target


def _run(command: list[str], timeout: int = 3600) -> None:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except FileNotFoundError as exc:
        raise ConversionError("找不到 FFmpeg。請先安裝 FFmpeg 並加入 PATH。") from exc
    except subprocess.TimeoutExpired as exc:
        raise ConversionError("轉換時間過長，已停止處理。") from exc

    if completed.returncode != 0:
        details = completed.stderr.strip().splitlines()
        message = details[-1] if details else "未知的 FFmpeg 錯誤"
        raise ConversionError(f"媒體轉換失敗：{message}")


def _ffprobe_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        duration = float(result.stdout.strip())
        if duration <= 0:
            raise ValueError
        return duration
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ConversionError("無法讀取影片長度，請確認檔案可正常播放且 FFprobe 已安裝。") from exc


def _zip_paths(zip_path: Path, items: Iterable[tuple[Path, str]]) -> Path:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path, archive_name in items:
            archive.write(file_path, archive_name)
    return zip_path


def _save_image(image: Image.Image, destination: Path) -> None:
    image.save(destination, "PNG", optimize=True)


def _open_flat_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image.seek(0)
        return image.convert("RGBA")


def _jpeg_bytes(image: Image.Image, quality: int) -> bytes:
    if image.mode != "RGB":
        background = Image.new("RGB", image.size, "white")
        if "A" in image.getbands():
            background.paste(image, mask=image.getchannel("A"))
        else:
            background.paste(image)
        image = background
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def _compress_image(source: Path, destination: Path, target_bytes: int) -> None:
    image = _open_flat_image(source)
    best = _jpeg_bytes(image, 15)

    for _ in range(9):
        low, high = 15, 95
        candidate = best
        while low <= high:
            quality = (low + high) // 2
            encoded = _jpeg_bytes(image, quality)
            if len(encoded) <= target_bytes:
                candidate = encoded
                low = quality + 1
            else:
                high = quality - 1

        if len(candidate) <= target_bytes:
            best = candidate
            break

        best = candidate
        scale = max(0.5, min(0.9, math.sqrt(target_bytes / max(len(candidate), 1)) * 0.92))
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        if new_size == image.size:
            break
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    destination.write_bytes(best)


def image_compress(files: list[tuple[Path, str]], output_dir: Path, target_mb: float) -> Path:
    generated: list[tuple[Path, str]] = []
    target_bytes = max(32_000, int(target_mb * 1024 * 1024))
    for source, original_name in files:
        name = f"{_safe_stem(original_name)}_compressed.jpg"
        destination = _unique_path(output_dir, name)
        _compress_image(source, destination, target_bytes)
        generated.append((destination, destination.name))
    if len(generated) == 1:
        return generated[0][0]
    return _zip_paths(output_dir / "compressed_images.zip", generated)


def images_to_pdf(files: list[tuple[Path, str]], output_dir: Path) -> Path:
    pages: list[Image.Image] = []
    try:
        for source, _ in files:
            image = _open_flat_image(source)
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            pages.append(background)
        if not pages:
            raise ConversionError("沒有可轉換的圖片。")
        destination = output_dir / "images.pdf"
        pages[0].save(destination, "PDF", save_all=True, append_images=pages[1:], resolution=150)
        return destination
    finally:
        for page in pages:
            page.close()


def image_noise(files: list[tuple[Path, str]], output_dir: Path, ratio: float) -> Path:
    generated: list[tuple[Path, str]] = []
    strength = max(0.0, min(1.0, ratio / 100.0))
    for source, original_name in files:
        image = _open_flat_image(source)
        rgb = image.convert("RGB")
        noise_l = Image.effect_noise(rgb.size, 72)
        noise = Image.merge("RGB", (noise_l, noise_l, noise_l))
        result = Image.blend(rgb, noise, strength)
        if "A" in image.getbands():
            result.putalpha(image.getchannel("A"))
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_noise.png")
        _save_image(result, destination)
        generated.append((destination, destination.name))
    if len(generated) == 1:
        return generated[0][0]
    return _zip_paths(output_dir / "noise_images.zip", generated)


def image_blur(files: list[tuple[Path, str]], output_dir: Path, pixels: float) -> Path:
    generated: list[tuple[Path, str]] = []
    for source, original_name in files:
        image = _open_flat_image(source)
        result = image.filter(ImageFilter.GaussianBlur(radius=pixels))
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_blur.png")
        _save_image(result, destination)
        generated.append((destination, destination.name))
    if len(generated) == 1:
        return generated[0][0]
    return _zip_paths(output_dir / "blurred_images.zip", generated)


def video_compress(files: list[tuple[Path, str]], output_dir: Path, target_mb: float) -> Path:
    generated: list[tuple[Path, str]] = []
    for index, (source, original_name) in enumerate(files):
        duration = _ffprobe_duration(source)
        total_kbps = max(160, int(target_mb * 8192 * 0.96 / duration))
        audio_kbps = 128 if total_kbps >= 400 else max(48, int(total_kbps * 0.22))
        video_kbps = max(100, total_kbps - audio_kbps)
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_compressed.mp4")
        passlog = output_dir / f"ffmpeg_pass_{index}"
        common = [
            "ffmpeg", "-y", "-i", str(source), "-map", "0:v:0", "-c:v", "libx264",
            "-preset", "medium", "-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k",
            "-bufsize", f"{video_kbps * 2}k", "-pix_fmt", "yuv420p", "-passlogfile", str(passlog),
        ]
        _run(common + ["-pass", "1", "-an", "-f", "mp4", os.devnull])
        _run(
            common
            + [
                "-pass", "2", "-map", "0:a:0?", "-c:a", "aac", "-b:a", f"{audio_kbps}k",
                "-movflags", "+faststart", str(destination),
            ]
        )
        for log in output_dir.glob(f"{passlog.name}*"):
            log.unlink(missing_ok=True)
        generated.append((destination, destination.name))
    if len(generated) == 1:
        return generated[0][0]
    return _zip_paths(output_dir / "compressed_videos.zip", generated)


def video_frames(files: list[tuple[Path, str]], output_dir: Path) -> Path:
    generated: list[tuple[Path, str]] = []
    frames_root = output_dir / "frames"
    frames_root.mkdir(exist_ok=True)
    for source, original_name in files:
        stem = _safe_stem(original_name)
        destination_dir = frames_root / stem
        suffix = 2
        while destination_dir.exists():
            destination_dir = frames_root / f"{stem}_{suffix}"
            suffix += 1
        destination_dir.mkdir()
        _run([
            "ffmpeg", "-y", "-i", str(source), "-vf", "fps=1", "-q:v", "2",
            str(destination_dir / "frame_%05d.jpg"),
        ])
        for frame in sorted(destination_dir.glob("*.jpg")):
            generated.append((frame, f"{destination_dir.name}/{frame.name}"))
    if not generated:
        raise ConversionError("影片中沒有可提取的畫面。")
    return _zip_paths(output_dir / "video_frames.zip", generated)


def video_audio(
    files: list[tuple[Path, str]], output_dir: Path, bitrate: int | str
) -> Path:
    generated: list[tuple[Path, str]] = []
    lossless = bitrate == "lossless"
    for source, original_name in files:
        extension = ".flac" if lossless else ".mp3"
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_audio{extension}")
        command = ["ffmpeg", "-y", "-i", str(source), "-vn"]
        if lossless:
            command += ["-c:a", "flac", str(destination)]
        else:
            command += ["-c:a", "libmp3lame", "-b:a", f"{int(bitrate)}k", str(destination)]
        _run(command)
        generated.append((destination, destination.name))
    if len(generated) == 1:
        return generated[0][0]
    return _zip_paths(output_dir / "extracted_audio.zip", generated)


def audio_volume(files: list[tuple[Path, str]], output_dir: Path, db: float) -> Path:
    generated: list[tuple[Path, str]] = []
    codec_by_suffix = {
        ".mp3": ("libmp3lame", ".mp3"),
        ".wav": ("pcm_s16le", ".wav"),
        ".flac": ("flac", ".flac"),
        ".m4a": ("aac", ".m4a"),
        ".aac": ("aac", ".m4a"),
        ".ogg": ("libvorbis", ".ogg"),
        ".opus": ("libopus", ".opus"),
    }
    for source, original_name in files:
        codec, extension = codec_by_suffix.get(Path(original_name).suffix.lower(), ("libmp3lame", ".mp3"))
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_{db:+g}dB{extension}")
        _run([
            "ffmpeg", "-y", "-i", str(source), "-filter:a", f"volume={db}dB",
            "-c:a", codec, str(destination),
        ])
        generated.append((destination, destination.name))
    if len(generated) == 1:
        return generated[0][0]
    return _zip_paths(output_dir / "adjusted_audio.zip", generated)


def merge_pdfs(files: list[tuple[Path, str]], output_dir: Path) -> Path:
    writer = PdfWriter()
    try:
        for source, _ in files:
            reader = PdfReader(str(source))
            if reader.is_encrypted:
                raise ConversionError("暫不支援有密碼保護的 PDF。")
            for page in reader.pages:
                writer.add_page(page)
        destination = output_dir / "merged.pdf"
        with destination.open("wb") as handle:
            writer.write(handle)
        return destination
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError("PDF 連接失敗，請確認檔案沒有損壞。") from exc
    finally:
        writer.close()


def pdf_to_images(files: list[tuple[Path, str]], output_dir: Path) -> Path:
    try:
        import fitz
    except ImportError as exc:
        raise ConversionError("缺少 PyMuPDF，請執行 pip install -r requirements.txt。") from exc

    generated: list[tuple[Path, str]] = []
    images_root = output_dir / "pdf_images"
    images_root.mkdir(exist_ok=True)
    for source, original_name in files:
        stem = _safe_stem(original_name)
        try:
            document = fitz.open(source)
            if document.needs_pass:
                raise ConversionError("暫不支援有密碼保護的 PDF。")
            for number, page in enumerate(document, start=1):
                destination = images_root / f"{stem}_page_{number:03d}.png"
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pixmap.save(destination)
                generated.append((destination, f"{stem}/{destination.name}"))
            document.close()
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"無法轉換 {original_name}。") from exc
    if not generated:
        raise ConversionError("PDF 中沒有可轉換的頁面。")
    return _zip_paths(output_dir / "pdf_images.zip", generated)


def convert(
    category: str,
    mode: str,
    files: list[tuple[Path, str]],
    output_dir: Path,
    options: dict,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if category == "image" and mode == "compress":
            return image_compress(files, output_dir, float(options["target_mb"]))
        if category == "image" and mode == "to_pdf":
            return images_to_pdf(files, output_dir)
        if category == "image" and mode == "noise":
            return image_noise(files, output_dir, float(options["ratio"]))
        if category == "image" and mode == "blur":
            return image_blur(files, output_dir, float(options["pixels"]))
        if category == "video" and mode == "compress":
            return video_compress(files, output_dir, float(options["target_mb"]))
        if category == "video" and mode == "extract_frames":
            return video_frames(files, output_dir)
        if category == "video" and mode == "extract_audio":
            bitrate = options.get("bitrate", 128)
            return video_audio(files, output_dir, bitrate if bitrate == "lossless" else int(bitrate))
        if category == "audio" and mode == "volume":
            return audio_volume(files, output_dir, float(options["db"]))
        if category == "pdf" and mode == "merge":
            return merge_pdfs(files, output_dir)
        if category == "pdf" and mode == "to_images":
            return pdf_to_images(files, output_dir)
    except (KeyError, TypeError, ValueError) as exc:
        raise ConversionError("轉換設定不完整或數值格式不正確。") from exc

    raise ConversionError("不支援的轉換模式。")


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
