from __future__ import annotations

import math
import os
import shutil
import subprocess
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable

from PIL import GifImagePlugin, Image, ImageFilter, ImageOps, ImageSequence
from pillow_heif import register_heif_opener
from pypdf import PdfReader, PdfWriter


register_heif_opener(thumbnails=False)

IMAGE_OUTPUT_FORMATS = {
    "png": ("PNG", ".png"),
    "jpeg": ("JPEG", ".jpg"),
    "gif": ("GIF", ".gif"),
    "heic": ("HEIF", ".heic"),
    "webp": ("WEBP", ".webp"),
    "bmp": ("BMP", ".bmp"),
    "tiff": ("TIFF", ".tiff"),
}


class ConversionError(RuntimeError):
    """A conversion error that is safe to show in the UI."""


ProgressCallback = Callable[[float, str | None], None]


def _report(progress: ProgressCallback | None, percent: float, filename: str | None = None) -> None:
    if progress:
        progress(max(0.0, min(99.0, percent)), filename)


def _file_progress(
    progress: ProgressCallback | None,
    file_index: int,
    file_count: int,
    filename: str,
    local_percent: float,
) -> None:
    overall = ((file_index + local_percent / 100.0) / max(file_count, 1)) * 94.0
    _report(progress, overall, filename)


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


def _run(
    command: list[str],
    timeout: int = 3600,
    progress_callback: Callable[[float], None] | None = None,
    duration: float | None = None,
) -> None:
    if progress_callback and duration and command and command[0].lower().startswith("ffmpeg"):
        progress_command = [
            command[0], "-v", "error", *command[1:-1],
            "-progress", "pipe:1", "-nostats", command[-1],
        ]
        try:
            process = subprocess.Popen(
                progress_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            assert process.stdout is not None
            for line in process.stdout:
                key, separator, value = line.strip().partition("=")
                if not separator:
                    continue
                if key in {"out_time_ms", "out_time_us"}:
                    try:
                        seconds = int(value) / 1_000_000
                        progress_callback(min(99.0, seconds / duration * 100))
                    except ValueError:
                        pass
                elif key == "progress" and value == "end":
                    progress_callback(100.0)
            process.wait(timeout=timeout)
            stderr = process.stderr.read() if process.stderr else ""
            process.stdout.close()
            if process.stderr:
                process.stderr.close()
        except FileNotFoundError as exc:
            raise ConversionError("找不到 FFmpeg。請先安裝 FFmpeg 並加入 PATH。") from exc
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
            raise ConversionError("轉換時間過長，已停止處理。") from exc

        if process.returncode != 0:
            details = stderr.strip().splitlines()
            message = details[-1] if details else "未知的 FFmpeg 錯誤"
            raise ConversionError(f"媒體轉換失敗：{message}")
        return

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


def image_preview(source: Path) -> BytesIO:
    with _open_flat_image(source) as image:
        image.thumbnail((480, 480), Image.Resampling.LANCZOS)
        return BytesIO(_jpeg_bytes(image, 85))


def detect_image_format(source: Path) -> str:
    try:
        with Image.open(source) as image:
            image_format = image.format or ""
    except (OSError, ValueError) as exc:
        raise ConversionError("無法辨識圖片格式，請確認檔案未損壞。") from exc
    return {"JPEG": "jpeg", "MPO": "jpeg", "HEIF": "heic", "TIFF": "tiff"}.get(
        image_format, image_format.lower()
    )


def validate_image_format_change(files: list[tuple[Path, str]], output_format: str) -> None:
    # Combining several inputs into a new animation also accepts existing GIFs.
    if output_format == "gif" and len(files) > 1:
        return
    for source, original_name in files:
        if detect_image_format(source) == output_format:
            label = output_format.upper()
            raise ConversionError(f"圖片「{original_name}」已是 {label} 格式，請選擇其他輸出格式。")


def _save_format_frame(image: Image.Image, destination: Path, output_format: str, **save_options) -> None:
    if output_format == "jpeg":
        destination.write_bytes(_jpeg_bytes(image, 95))
    elif output_format == "bmp":
        with Image.new("RGB", image.size, "white") as background:
            background.paste(image, mask=image.getchannel("A"))
            background.save(destination, "BMP")
    else:
        if output_format in {"heic", "webp"}:
            save_options["quality"] = 90
        image.save(destination, IMAGE_OUTPUT_FORMATS[output_format][0], **save_options)


def _convert_image_format(source: Path, destination: Path, output_format: str) -> list[Path]:
    frames: list[Image.Image] = []
    durations: list[int] = []
    generated: list[Path] = []
    try:
        with Image.open(source) as image:
            animated = getattr(image, "is_animated", False)
            split_frames = animated and output_format not in {"gif", "webp"}
            loop = image.info.get("loop")
            for index, frame in enumerate(ImageSequence.Iterator(image), start=1):
                with ImageOps.exif_transpose(frame) as oriented:
                    rgba = oriented.convert("RGBA")
                if split_frames:
                    frame_path = _unique_path(
                        destination.parent, f"{destination.stem}_frame_{index:04d}{destination.suffix}"
                    )
                    with rgba:
                        _save_format_frame(rgba, frame_path, output_format)
                    generated.append(frame_path)
                else:
                    frames.append(rgba)
                    durations.append(frame.info.get("duration", 100))
                if not animated:
                    break

            if split_frames:
                return generated

            save_options = {}
            if animated:
                save_options.update(save_all=True, append_images=frames[1:], duration=durations)
                if loop is not None:
                    save_options["loop"] = loop
                elif output_format == "webp":
                    save_options["loop"] = 1
                if output_format == "gif":
                    save_options["disposal"] = 2
            _save_format_frame(frames[0], destination, output_format, **save_options)
            return [destination]
    finally:
        for frame in frames:
            frame.close()


def _gif_palette(image: Image.Image) -> Image.Image:
    with image.convert("RGB") as rgb:
        indexed = rgb.quantize(colors=255)
    palette = indexed.getpalette() or []
    palette.extend([0] * (768 - len(palette)))
    palette[765:768] = [0, 0, 0]
    indexed.putpalette(palette)
    with image.getchannel("A") as alpha:
        with alpha.point(lambda value: 255 if value < 128 else 0) as transparent:
            indexed.paste(255, mask=transparent)
    return indexed


def images_to_gif(
    files: list[tuple[Path, str]],
    output_dir: Path,
    progress: ProgressCallback | None = None,
    fps: int | None = None,
) -> Path:
    width = height = 0
    frame_counts = []
    loop = 0
    for index, (source, original_name) in enumerate(files):
        with Image.open(source) as image:
            if len(files) == 1:
                loop = image.info.get("loop", 0)
            count = 0
            for frame in ImageSequence.Iterator(image):
                frame_width, frame_height = frame.size
                if frame.getexif().get(274) in {5, 6, 7, 8}:
                    frame_width, frame_height = frame_height, frame_width
                width = max(width, frame_width)
                height = max(height, frame_height)
                count += 1
            frame_counts.append(count)
        _report(progress, (index + 1) / len(files) * 8, original_name)

    destination = output_dir / (f"{_safe_stem(files[0][1])}.gif" if len(files) == 1 else "animated_images.gif")
    first_frame = True
    frame_number = 0
    with destination.open("wb") as output:
        for file_index, (source, original_name) in enumerate(files):
            with Image.open(source) as image:
                for frame_index, frame in enumerate(ImageSequence.Iterator(image)):
                    frame.load()
                    if fps is None:
                        duration = frame.info.get("duration") or 100
                    else:
                        # GIF delays use 10 ms units. Round cumulative boundaries
                        # so rates such as 24 or 30 FPS keep the requested average.
                        start_tick = round(frame_number * 100 / fps)
                        end_tick = round((frame_number + 1) * 100 / fps)
                        duration = (end_tick - start_tick) * 10
                    frame_number += 1
                    with ImageOps.exif_transpose(frame) as oriented:
                        with oriented.convert("RGBA") as rgba:
                            with Image.new("RGBA", (width, height), (0, 0, 0, 0)) as canvas:
                                canvas.paste(rgba, ((width - rgba.width) // 2, (height - rgba.height) // 2))
                                with _gif_palette(canvas) as indexed:
                                    # Write one frame at a time instead of retaining every
                                    # decoded image in memory. Identical frames stay separate.
                                    if first_frame:
                                        header, _ = GifImagePlugin.getheader(indexed, info={
                                            "loop": loop, "background": 255, "transparency": 255,
                                            "optimize": False,
                                        })
                                        output.writelines(header)
                                        first_frame = False
                                    output.writelines(GifImagePlugin.getdata(
                                        indexed, duration=duration, disposal=2,
                                        transparency=255, include_color_table=True,
                                    ))
                    fraction = (frame_index + 1) / frame_counts[file_index]
                    _report(progress, 8 + (file_index + fraction) / len(files) * 86, original_name)
        output.write(b";")
    _report(progress, 98)
    return destination


def image_convert_format(
    files: list[tuple[Path, str]],
    output_dir: Path,
    output_format: str,
    progress: ProgressCallback | None = None,
    fps: int | None = None,
) -> Path:
    if output_format not in IMAGE_OUTPUT_FORMATS:
        raise ConversionError("不支援的圖片輸出格式。")
    validate_image_format_change(files, output_format)
    if output_format == "gif":
        try:
            return images_to_gif(files, output_dir, progress, fps=fps)
        except OSError as exc:
            raise ConversionError("無法建立 GIF，請確認上傳圖片未損壞。") from exc
    _, extension = IMAGE_OUTPUT_FORMATS[output_format]
    generated: list[tuple[Path, str]] = []
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 5)
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}{extension}")
        try:
            paths = _convert_image_format(source, destination, output_format)
        except OSError as exc:
            raise ConversionError(f"無法轉換圖片「{original_name}」，請確認檔案未損壞且格式受支援。") from exc
        generated.extend((path, path.name) for path in paths)
        _file_progress(progress, index, len(files), original_name, 100)
    result = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "converted_images.zip", generated)
    _report(progress, 98)
    return result


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


def image_compress(
    files: list[tuple[Path, str]],
    output_dir: Path,
    target_mb: float,
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    target_bytes = max(32_000, int(target_mb * 1024 * 1024))
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 5)
        name = f"{_safe_stem(original_name)}_compressed.jpg"
        destination = _unique_path(output_dir, name)
        _compress_image(source, destination, target_bytes)
        generated.append((destination, destination.name))
        _file_progress(progress, index, len(files), original_name, 100)
    result = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "compressed_images.zip", generated)
    _report(progress, 98)
    return result


def images_to_pdf(
    files: list[tuple[Path, str]], output_dir: Path, progress: ProgressCallback | None = None
) -> Path:
    pages: list[Image.Image] = []
    try:
        for index, (source, original_name) in enumerate(files):
            _file_progress(progress, index, len(files), original_name, 10)
            image = _open_flat_image(source)
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            pages.append(background)
            _file_progress(progress, index, len(files), original_name, 85)
        if not pages:
            raise ConversionError("沒有可轉換的圖片。")
        destination = output_dir / "images.pdf"
        pages[0].save(destination, "PDF", save_all=True, append_images=pages[1:], resolution=150)
        _report(progress, 98)
        return destination
    finally:
        for page in pages:
            page.close()


def image_noise(
    files: list[tuple[Path, str]],
    output_dir: Path,
    ratio: float,
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    strength = max(0.0, min(1.0, ratio / 100.0))
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 5)
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
        _file_progress(progress, index, len(files), original_name, 100)
    result_path = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "noise_images.zip", generated)
    _report(progress, 98)
    return result_path


def image_blur(
    files: list[tuple[Path, str]],
    output_dir: Path,
    pixels: float,
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 5)
        image = _open_flat_image(source)
        result = image.filter(ImageFilter.GaussianBlur(radius=pixels))
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_blur.png")
        _save_image(result, destination)
        generated.append((destination, destination.name))
        _file_progress(progress, index, len(files), original_name, 100)
    result_path = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "blurred_images.zip", generated)
    _report(progress, 98)
    return result_path


def video_compress(
    files: list[tuple[Path, str]],
    output_dir: Path,
    target_mb: float,
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
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
        _run(
            common + ["-pass", "1", "-an", "-f", "mp4", os.devnull],
            progress_callback=lambda value, i=index, name=original_name: _file_progress(
                progress, i, len(files), name, value * 0.48
            ),
            duration=duration,
        )
        _run(
            common
            + [
                "-pass", "2", "-map", "0:a:0?", "-c:a", "aac", "-b:a", f"{audio_kbps}k",
                "-movflags", "+faststart", str(destination),
            ],
            progress_callback=lambda value, i=index, name=original_name: _file_progress(
                progress, i, len(files), name, 48 + value * 0.52
            ),
            duration=duration,
        )
        for log in output_dir.glob(f"{passlog.name}*"):
            log.unlink(missing_ok=True)
        generated.append((destination, destination.name))
    result = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "compressed_videos.zip", generated)
    _report(progress, 98)
    return result


def video_split(
    files: list[tuple[Path, str]],
    output_dir: Path,
    segment_minutes: float,
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    segments_root = output_dir / "segments"
    segments_root.mkdir(exist_ok=True)
    segment_seconds = max(1.0, segment_minutes * 60.0)

    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
        duration = _ffprobe_duration(source)
        stem = _safe_stem(original_name)
        destination_dir = segments_root / f"{stem}_segments"
        suffix = 2
        while destination_dir.exists():
            destination_dir = segments_root / f"{stem}_segments_{suffix}"
            suffix += 1
        destination_dir.mkdir()
        output_pattern = destination_dir / "part_%03d.mp4"
        command = [
            "ffmpeg", "-y", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-sc_threshold", "0",
            "-force_key_frames", f"expr:gte(t,n_forced*{segment_seconds:g})",
            "-c:a", "aac", "-b:a", "192k",
            "-f", "segment", "-segment_time", f"{segment_seconds:g}",
            "-segment_time_delta", "0.05", "-segment_start_number", "1",
            "-reset_timestamps", "1", str(output_pattern),
        ]
        _run(
            command,
            progress_callback=lambda value, i=index, name=original_name: _file_progress(
                progress, i, len(files), name, value
            ),
            duration=duration,
        )
        segments = sorted(destination_dir.glob("part_*.mp4"))
        if not segments:
            raise ConversionError(f"無法分割 {original_name}。")
        for segment in segments:
            generated.append((segment, f"{destination_dir.name}/{segment.name}"))

    result = _zip_paths(output_dir / "split_videos.zip", generated)
    _report(progress, 98)
    return result


def video_frames(
    files: list[tuple[Path, str]],
    output_dir: Path,
    frame_mode: str = "second",
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    frames_root = output_dir / "frames"
    frames_root.mkdir(exist_ok=True)
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
        duration = _ffprobe_duration(source)
        stem = _safe_stem(original_name)
        destination_dir = frames_root / stem
        suffix = 2
        while destination_dir.exists():
            destination_dir = frames_root / f"{stem}_{suffix}"
            suffix += 1
        destination_dir.mkdir()
        command = ["ffmpeg", "-y", "-i", str(source), "-map", "0:v:0"]
        if frame_mode == "all":
            command += ["-fps_mode", "passthrough"]
        else:
            command += ["-vf", "fps=1"]
        command += ["-q:v", "2", str(destination_dir / "frame_%05d.jpg")]
        _run(
            command,
            progress_callback=lambda value, i=index, name=original_name: _file_progress(
                progress, i, len(files), name, value
            ),
            duration=duration,
        )
        for frame in sorted(destination_dir.glob("*.jpg")):
            generated.append((frame, f"{destination_dir.name}/{frame.name}"))
    if not generated:
        raise ConversionError("影片中沒有可提取的畫面。")
    result = _zip_paths(output_dir / "video_frames.zip", generated)
    _report(progress, 98)
    return result


def video_audio(
    files: list[tuple[Path, str]],
    output_dir: Path,
    bitrate: int | str,
    progress: ProgressCallback | None = None,
) -> Path:
    generated: list[tuple[Path, str]] = []
    lossless = bitrate == "lossless"
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
        duration = _ffprobe_duration(source)
        extension = ".flac" if lossless else ".mp3"
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_audio{extension}")
        command = ["ffmpeg", "-y", "-i", str(source), "-vn"]
        if lossless:
            command += ["-c:a", "flac", str(destination)]
        else:
            command += ["-c:a", "libmp3lame", "-b:a", f"{int(bitrate)}k", str(destination)]
        _run(
            command,
            progress_callback=lambda value, i=index, name=original_name: _file_progress(
                progress, i, len(files), name, value
            ),
            duration=duration,
        )
        generated.append((destination, destination.name))
    result = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "extracted_audio.zip", generated)
    _report(progress, 98)
    return result


def audio_volume(
    files: list[tuple[Path, str]],
    output_dir: Path,
    db: float,
    progress: ProgressCallback | None = None,
) -> Path:
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
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
        duration = _ffprobe_duration(source)
        codec, extension = codec_by_suffix.get(Path(original_name).suffix.lower(), ("libmp3lame", ".mp3"))
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}_{db:+g}dB{extension}")
        _run(
            [
                "ffmpeg", "-y", "-i", str(source), "-filter:a", f"volume={db}dB",
                "-c:a", codec, str(destination),
            ],
            progress_callback=lambda value, i=index, name=original_name: _file_progress(
                progress, i, len(files), name, value
            ),
            duration=duration,
        )
        generated.append((destination, destination.name))
    result = generated[0][0] if len(generated) == 1 else _zip_paths(output_dir / "adjusted_audio.zip", generated)
    _report(progress, 98)
    return result


def pdf_compress(
    files: list[tuple[Path, str]],
    output_dir: Path,
    target_mb: float,
    progress: ProgressCallback | None = None,
) -> Path:
    try:
        import fitz
    except ImportError as exc:
        raise ConversionError("缺少 PyMuPDF，請執行 pip install -r requirements.txt。") from exc

    target_bytes = max(32_000, int(target_mb * 1024 * 1024))
    generated: list[tuple[Path, str]] = []
    profiles = [
        (320, 300, 94),
        (280, 260, 92),
        (240, 220, 90),
        (210, 190, 87),
        (180, 160, 84),
        (150, 135, 80),
        (125, 110, 74),
        (100, 90, 68),
        (73, 72, 60),
    ]

    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
        work_dir = output_dir / f"pdf_compress_{index}"
        work_dir.mkdir()
        best_path = source
        best_size = source.stat().st_size
        has_images = False

        try:
            lossless_path = work_dir / "lossless.pdf"
            document = fitz.open(source)
            if document.needs_pass:
                document.close()
                raise ConversionError("暫不支援有密碼保護的 PDF。")
            has_images = any(page.get_images(full=True) for page in document)
            document.save(
                lossless_path,
                garbage=4,
                clean=True,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                use_objstms=1,
                compression_effort=100,
            )
            document.close()
            if lossless_path.stat().st_size < best_size:
                best_path = lossless_path
                best_size = lossless_path.stat().st_size
            _file_progress(progress, index, len(files), original_name, 16)

            if best_size > target_bytes and has_images:
                for profile_index, (threshold, dpi, quality) in enumerate(profiles):
                    candidate = work_dir / f"candidate_{profile_index}.pdf"
                    document = fitz.open(source)
                    document.rewrite_images(
                        dpi_threshold=threshold,
                        dpi_target=dpi,
                        quality=quality,
                        lossy=True,
                        lossless=True,
                        bitonal=False,
                        color=True,
                        gray=True,
                    )
                    document.save(
                        candidate,
                        garbage=4,
                        clean=True,
                        deflate=True,
                        deflate_images=True,
                        deflate_fonts=True,
                        use_objstms=1,
                        compression_effort=100,
                    )
                    document.close()
                    candidate_size = candidate.stat().st_size
                    if candidate_size < best_size:
                        best_path = candidate
                        best_size = candidate_size
                    local_percent = 16 + (profile_index + 1) / len(profiles) * 79
                    _file_progress(
                        progress, index, len(files), original_name, local_percent
                    )
                    if candidate_size <= target_bytes:
                        best_path = candidate
                        break

            destination = _unique_path(
                output_dir, f"{_safe_stem(original_name)}_compressed.pdf"
            )
            shutil.copyfile(best_path, destination)
            generated.append((destination, destination.name))
            _file_progress(progress, index, len(files), original_name, 100)
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"無法壓縮 {original_name}。") from exc
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    result = (
        generated[0][0]
        if len(generated) == 1
        else _zip_paths(output_dir / "compressed_pdfs.zip", generated)
    )
    _report(progress, 98)
    return result


def merge_pdfs(
    files: list[tuple[Path, str]], output_dir: Path, progress: ProgressCallback | None = None
) -> Path:
    writer = PdfWriter()
    try:
        for index, (source, original_name) in enumerate(files):
            _file_progress(progress, index, len(files), original_name, 5)
            reader = PdfReader(str(source))
            if reader.is_encrypted:
                raise ConversionError("暫不支援有密碼保護的 PDF。")
            for page in reader.pages:
                writer.add_page(page)
            _file_progress(progress, index, len(files), original_name, 90)
        destination = output_dir / "merged.pdf"
        with destination.open("wb") as handle:
            writer.write(handle)
        _report(progress, 98)
        return destination
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError("PDF 連接失敗，請確認檔案沒有損壞。") from exc
    finally:
        writer.close()


def pdf_to_images(
    files: list[tuple[Path, str]], output_dir: Path, progress: ProgressCallback | None = None
) -> Path:
    try:
        import fitz
    except ImportError as exc:
        raise ConversionError("缺少 PyMuPDF，請執行 pip install -r requirements.txt。") from exc

    generated: list[tuple[Path, str]] = []
    images_root = output_dir / "pdf_images"
    images_root.mkdir(exist_ok=True)
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 1)
        stem = _safe_stem(original_name)
        try:
            document = fitz.open(source)
            if document.needs_pass:
                raise ConversionError("暫不支援有密碼保護的 PDF。")
            page_count = max(document.page_count, 1)
            for number, page in enumerate(document, start=1):
                destination = images_root / f"{stem}_page_{number:03d}.png"
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pixmap.save(destination)
                generated.append((destination, f"{stem}/{destination.name}"))
                _file_progress(progress, index, len(files), original_name, number / page_count * 100)
            document.close()
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"無法轉換 {original_name}。") from exc
    if not generated:
        raise ConversionError("PDF 中沒有可轉換的頁面。")
    result = _zip_paths(output_dir / "pdf_images.zip", generated)
    _report(progress, 98)
    return result


def markdown_to_pdf(
    files: list[tuple[Path, str]],
    output_dir: Path,
    options: dict,
    progress: ProgressCallback | None = None,
) -> Path:
    from markdown_converter import MarkdownRenderError, render_markdown_pdf

    generated: list[tuple[Path, str]] = []
    for index, (source, original_name) in enumerate(files):
        _file_progress(progress, index, len(files), original_name, 5)
        work_dir = output_dir / f"markdown_render_{index}"
        work_dir.mkdir()
        destination = _unique_path(output_dir, f"{_safe_stem(original_name)}.pdf")
        try:
            _file_progress(progress, index, len(files), original_name, 22)
            render_markdown_pdf(source, destination, options, work_dir)
            generated.append((destination, destination.name))
            _file_progress(progress, index, len(files), original_name, 100)
        except MarkdownRenderError as exc:
            raise ConversionError(str(exc)) from exc
        except Exception as exc:
            raise ConversionError(f"無法將 {original_name} 轉換為 PDF。") from exc
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    result = (
        generated[0][0]
        if len(generated) == 1
        else _zip_paths(output_dir / "markdown_pdfs.zip", generated)
    )
    _report(progress, 98)
    return result


def convert(
    category: str,
    mode: str,
    files: list[tuple[Path, str]],
    output_dir: Path,
    options: dict,
    progress: ProgressCallback | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if category == "image" and mode == "compress":
            return image_compress(files, output_dir, float(options["target_mb"]), progress)
        if category == "image" and mode == "convert_format":
            return image_convert_format(files, output_dir, options["format"], progress, fps=options.get("fps"))
        if category == "image" and mode == "to_pdf":
            return images_to_pdf(files, output_dir, progress)
        if category == "image" and mode == "noise":
            return image_noise(files, output_dir, float(options["ratio"]), progress)
        if category == "image" and mode == "blur":
            return image_blur(files, output_dir, float(options["pixels"]), progress)
        if category == "video" and mode == "compress":
            return video_compress(files, output_dir, float(options["target_mb"]), progress)
        if category == "video" and mode == "split":
            return video_split(
                files, output_dir, float(options["segment_minutes"]), progress
            )
        if category == "video" and mode == "extract_frames":
            return video_frames(files, output_dir, options.get("frame_mode", "second"), progress)
        if category == "video" and mode == "extract_audio":
            bitrate = options.get("bitrate", 128)
            return video_audio(
                files, output_dir, bitrate if bitrate == "lossless" else int(bitrate), progress
            )
        if category == "audio" and mode == "volume":
            return audio_volume(files, output_dir, float(options["db"]), progress)
        if category == "pdf" and mode == "compress":
            return pdf_compress(
                files, output_dir, float(options["target_mb"]), progress
            )
        if category == "pdf" and mode == "merge":
            return merge_pdfs(files, output_dir, progress)
        if category == "pdf" and mode == "to_images":
            return pdf_to_images(files, output_dir, progress)
        if category == "markdown" and mode == "to_pdf":
            return markdown_to_pdf(files, output_dir, options, progress)
    except (KeyError, TypeError, ValueError) as exc:
        raise ConversionError("轉換設定不完整或數值格式不正確。") from exc

    raise ConversionError("不支援的轉換模式。")


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
