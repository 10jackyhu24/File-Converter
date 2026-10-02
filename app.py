from __future__ import annotations

import json
import mimetypes
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from converter import ConversionError, convert, reset_output_dir


BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "data" / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=2 * 1024 * 1024 * 1024,
    JSON_AS_ASCII=False,
)

conversion_tasks: dict[str, dict] = {}
conversion_tasks_lock = threading.Lock()

CATEGORY_EXTENSIONS = {
    "image": {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"},
    "video": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpeg", ".mpg"},
    "audio": {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"},
    "pdf": {".pdf"},
}

VALID_MODES = {
    "image": {"compress", "to_pdf", "noise", "blur"},
    "video": {"compress", "split", "extract_frames", "extract_audio"},
    "audio": {"volume"},
    "pdf": {"compress", "merge", "to_images"},
}


def _json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def _job_dir(job_id: str) -> Path | None:
    try:
        canonical = str(uuid.UUID(job_id))
    except (ValueError, TypeError, AttributeError):
        return None
    path = (JOBS_DIR / canonical).resolve()
    if path.parent != JOBS_DIR.resolve():
        return None
    return path


def _read_metadata(job_dir: Path) -> dict | None:
    metadata_file = job_dir / "job.json"
    if not metadata_file.is_file():
        return None
    try:
        return json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_metadata(job_dir: Path, metadata: dict) -> None:
    (job_dir / "job.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _task_snapshot(job_id: str) -> dict | None:
    with conversion_tasks_lock:
        task = conversion_tasks.get(job_id)
        return dict(task) if task else None


def _update_task(job_id: str, **values) -> None:
    with conversion_tasks_lock:
        task = conversion_tasks.setdefault(job_id, {})
        if "progress" in values:
            values["progress"] = max(float(task.get("progress", 0)), float(values["progress"]))
        task.update(values)


def _start_task(job_id: str) -> None:
    with conversion_tasks_lock:
        conversion_tasks[job_id] = {
            "status": "queued",
            "progress": 0,
            "filename": None,
            "error": None,
        }


def _run_conversion(
    job_id: str,
    job_dir: Path,
    metadata: dict,
    category: str,
    mode: str,
    files: list[tuple[Path, str]],
    options: dict,
) -> None:
    with app.app_context():
        try:
            output_dir = job_dir / "output"
            reset_output_dir(output_dir)
            _update_task(job_id, status="processing", progress=1, filename=None)

            def report(percent: float, filename: str | None = None) -> None:
                _update_task(
                    job_id,
                    status="processing",
                    progress=round(percent, 1),
                    filename=filename,
                )

            result = convert(category, mode, files, output_dir, options, report)
            if not result.is_file():
                raise ConversionError("轉換沒有產生輸出檔案。")

            _update_task(job_id, status="finalizing", progress=99, filename=None)
            metadata["result"] = {
                "name": result.name,
                "size": result.stat().st_size,
                "created_at": time.time(),
            }
            _write_metadata(job_dir, metadata)
            _update_task(
                job_id,
                status="completed",
                progress=100,
                filename=result.name,
                size=result.stat().st_size,
                download_url=f"/api/jobs/{job_id}/download",
            )
        except ConversionError as exc:
            _update_task(job_id, status="failed", error=str(exc), filename=None)
        except Exception:
            app.logger.exception("Background conversion failed")
            _update_task(
                job_id,
                status="failed",
                error="轉換時發生未預期的錯誤。",
                filename=None,
            )


def _cleanup_expired_jobs(max_age_hours: int = 24) -> None:
    cutoff = time.time() - max_age_hours * 3600
    try:
        for path in JOBS_DIR.iterdir():
            if path.is_dir() and path.stat().st_mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                with conversion_tasks_lock:
                    conversion_tasks.pop(path.name, None)
    except OSError:
        pass


def _public_file(file_item: dict) -> dict:
    return {
        "id": file_item["id"],
        "name": file_item["original_name"],
        "size": file_item["size"],
        "mime": file_item["mime"],
    }


def _number(value, label: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ConversionError(f"{label}必須是數字。") from exc
    if not minimum <= number <= maximum:
        raise ConversionError(f"{label}必須介於 {minimum:g} 到 {maximum:g}。")
    return number


def _validate_options(category: str, mode: str, options: dict) -> dict:
    if category in {"image", "video", "pdf"} and mode == "compress":
        return {"target_mb": _number(options.get("target_mb"), "目標大小", 0.1, 2048)}
    if category == "image" and mode == "noise":
        return {"ratio": _number(options.get("ratio"), "雜訊比例", 0, 100)}
    if category == "image" and mode == "blur":
        return {"pixels": _number(options.get("pixels"), "模糊像素", 0, 100)}
    if category == "video" and mode == "extract_audio":
        bitrate = options.get("bitrate", 128)
        if bitrate == "lossless":
            return {"bitrate": bitrate}
        return {"bitrate": int(_number(bitrate, "音訊位元率", 16, 512))}
    if category == "video" and mode == "split":
        return {
            "segment_minutes": _number(
                options.get("segment_minutes"), "每段分鐘數", 0.01, 1440
            )
        }
    if category == "video" and mode == "extract_frames":
        frame_mode = options.get("frame_mode", "second")
        if frame_mode not in {"second", "all"}:
            raise ConversionError("圖片提取頻率不正確。")
        return {"frame_mode": frame_mode}
    if category == "audio" and mode == "volume":
        return {"db": _number(options.get("db"), "音量", -30, 30)}
    return {}


@app.get("/")
def index():
    _cleanup_expired_jobs()
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "File Converter"})


@app.post("/api/upload")
def upload():
    _cleanup_expired_jobs()
    category = request.form.get("category", "")
    if category not in CATEGORY_EXTENSIONS:
        return _json_error("不支援的檔案類型。")

    incoming = [item for item in request.files.getlist("files") if item and item.filename]
    if not incoming:
        return _json_error("請至少選擇一個檔案。")
    if len(incoming) > 50:
        return _json_error("一次最多可上傳 50 個檔案。")

    invalid = [
        item.filename
        for item in incoming
        if Path(item.filename).suffix.lower() not in CATEGORY_EXTENSIONS[category]
    ]
    if invalid:
        return _json_error(f"檔案格式不符：{', '.join(invalid[:3])}")

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    upload_dir = job_dir / "uploads"
    upload_dir.mkdir(parents=True)
    file_records = []

    try:
        for index, item in enumerate(incoming):
            original_name = Path(item.filename).name
            cleaned = secure_filename(original_name) or f"file_{index}{Path(original_name).suffix.lower()}"
            file_id = uuid.uuid4().hex
            stored_name = f"{index:03d}_{file_id}_{cleaned}"
            destination = upload_dir / stored_name
            item.save(destination)
            if destination.stat().st_size == 0:
                raise ConversionError(f"{original_name} 是空檔案。")
            file_records.append(
                {
                    "id": file_id,
                    "original_name": original_name,
                    "stored_name": stored_name,
                    "size": destination.stat().st_size,
                    "mime": item.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream",
                }
            )

        metadata = {
            "job_id": job_id,
            "category": category,
            "created_at": time.time(),
            "files": file_records,
            "result": None,
        }
        _write_metadata(job_dir, metadata)
        return jsonify({"ok": True, "job_id": job_id, "files": [_public_file(f) for f in file_records]})
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        if isinstance(exc, ConversionError):
            return _json_error(str(exc))
        app.logger.exception("Upload failed")
        return _json_error("上傳失敗，請稍後再試。", 500)


@app.delete("/api/jobs/<job_id>/files/<file_id>")
def delete_file(job_id: str, file_id: str):
    job_dir = _job_dir(job_id)
    if not job_dir or not job_dir.is_dir():
        return _json_error("找不到這次上傳記錄。", 404)
    metadata = _read_metadata(job_dir)
    if not metadata:
        return _json_error("上傳記錄已損壞。", 404)
    match = next((item for item in metadata["files"] if item["id"] == file_id), None)
    if not match:
        return _json_error("找不到該檔案。", 404)
    (job_dir / "uploads" / match["stored_name"]).unlink(missing_ok=True)
    metadata["files"] = [item for item in metadata["files"] if item["id"] != file_id]
    _write_metadata(job_dir, metadata)
    return jsonify({"ok": True})


@app.post("/api/convert")
def convert_files():
    payload = request.get_json(silent=True) or {}
    job_dir = _job_dir(payload.get("job_id"))
    if not job_dir or not job_dir.is_dir():
        return _json_error("上傳記錄不存在或已過期，請重新上傳。", 404)

    metadata = _read_metadata(job_dir)
    if not metadata:
        return _json_error("無法讀取上傳記錄。", 404)
    category = metadata["category"]
    mode = payload.get("mode")
    if mode not in VALID_MODES.get(category, set()):
        return _json_error("不支援的轉換模式。")

    order = payload.get("file_ids") or []
    records_by_id = {item["id"]: item for item in metadata["files"]}
    if not order or len(order) != len(set(order)) or any(item not in records_by_id for item in order):
        return _json_error("檔案清單不正確，請重新整理後再試。")
    if category == "pdf" and mode == "merge" and len(order) < 2:
        return _json_error("連接 PDF 至少需要兩個檔案。")

    active_task = _task_snapshot(metadata["job_id"])
    if active_task and active_task.get("status") in {"queued", "processing", "finalizing"}:
        return _json_error("此工作正在處理中，請稍候。", 409)

    try:
        options = _validate_options(category, mode, payload.get("options") or {})
    except ConversionError as exc:
        return _json_error(str(exc))

    files = [
        (
            job_dir / "uploads" / records_by_id[file_id]["stored_name"],
            records_by_id[file_id]["original_name"],
        )
        for file_id in order
    ]
    if any(not path.is_file() for path, _ in files):
        return _json_error("部分上傳檔案已不存在，請重新上傳。", 404)

    metadata["result"] = None
    _write_metadata(job_dir, metadata)
    _start_task(metadata["job_id"])
    worker = threading.Thread(
        target=_run_conversion,
        args=(metadata["job_id"], job_dir, metadata, category, mode, files, options),
        name=f"conversion-{metadata['job_id'][:8]}",
        daemon=True,
    )
    worker.start()
    return (
        jsonify(
            {
                "ok": True,
                "status": "queued",
                "status_url": f"/api/jobs/{metadata['job_id']}/status",
            }
        ),
        202,
    )


@app.get("/api/jobs/<job_id>/status")
def conversion_status(job_id: str):
    job_dir = _job_dir(job_id)
    if not job_dir or not job_dir.is_dir():
        return _json_error("上傳記錄不存在或已過期。", 404)
    task = _task_snapshot(job_id)
    if not task:
        return jsonify({"ok": True, "status": "idle", "progress": 0})
    return jsonify({"ok": True, **task})


@app.get("/api/jobs/<job_id>/download")
def download(job_id: str):
    job_dir = _job_dir(job_id)
    if not job_dir or not job_dir.is_dir():
        return _json_error("下載已過期。", 404)
    metadata = _read_metadata(job_dir)
    if not metadata or not metadata.get("result"):
        return _json_error("找不到轉換結果。", 404)
    result = job_dir / "output" / metadata["result"]["name"]
    if not result.is_file() or result.parent.resolve() != (job_dir / "output").resolve():
        return _json_error("找不到轉換結果。", 404)
    return send_file(result, as_attachment=True, download_name=result.name)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return _json_error("上傳內容超過 2 GB 上限。", 413)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"\nFile Converter 已啟動：http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
