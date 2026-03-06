import threading
import uuid
import time
import os
from dataclasses import dataclass, field
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from database import SessionLocal
from models import Video, Setting
from processor import process_video_file

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm"}


@dataclass
class Task:
    id: str
    scan_type: str          # "all", "thumbnail", "preview"
    directory: str
    status: str = "pending"  # "pending", "running", "completed", "cancelled", "error"
    total: int = 0
    current: int = 0
    current_file: str = ""
    cancel_flag: bool = False
    error_message: str = ""


class TaskQueue:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_concurrent = 2

    def _get_max_concurrent(self):
        """Read max_concurrent_tasks from DB, fallback to 2."""
        try:
            db = SessionLocal()
            setting = db.query(Setting).filter(Setting.key == "max_concurrent_tasks").first()
            db.close()
            if setting:
                return max(1, int(setting.value))
        except Exception:
            pass
        return 2

    def _ensure_executor(self):
        new_max = self._get_max_concurrent()
        if self._executor is None or new_max != self._max_concurrent:
            if self._executor is not None:
                # Don't shut down — let existing tasks finish, but create a new one
                # for new tasks with updated concurrency
                pass
            self._max_concurrent = new_max
            self._executor = ThreadPoolExecutor(max_workers=self._max_concurrent)

    def submit(self, scan_type: str, directory: str) -> Task:
        """Submit a new scan task. Returns the Task object."""
        task = Task(
            id=str(uuid.uuid4())[:8],
            scan_type=scan_type,
            directory=directory,
        )
        with self._lock:
            self.tasks[task.id] = task

        self._ensure_executor()
        self._executor.submit(self._run_task, task)
        return task

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            task.cancel_flag = True
            if task.status == "pending":
                task.status = "cancelled"
            return True

    def get_all_tasks(self) -> list[dict]:
        with self._lock:
            result = []
            for t in self.tasks.values():
                result.append({
                    "id": t.id,
                    "scan_type": t.scan_type,
                    "directory": t.directory,
                    "status": t.status,
                    "total": t.total,
                    "current": t.current,
                    "current_file": t.current_file,
                    "error_message": t.error_message,
                })
            return result

    def clear_finished(self):
        """Remove completed/cancelled/error tasks."""
        with self._lock:
            finished = [tid for tid, t in self.tasks.items()
                        if t.status in ("completed", "cancelled", "error")]
            for tid in finished:
                del self.tasks[tid]

    def _run_task(self, task: Task):
        """Execute the scan in a worker thread."""
        task.status = "running"
        task.current_file = "Initializing..."

        if not task.directory or not os.path.exists(task.directory):
            task.status = "error"
            task.error_message = f"Invalid directory: {task.directory}"
            return

        # Each thread gets its own DB session
        db = SessionLocal()

        try:
            # Read settings
            thumb_pct_setting = db.query(Setting).filter(Setting.key == "thumbnail_percentage").first()
            thumb_pct = float(thumb_pct_setting.value) if thumb_pct_setting else 5.0

            skip_scanned_setting = db.query(Setting).filter(Setting.key == "skip_scanned").first()
            skip_scanned = skip_scanned_setting.value == "true" if skip_scanned_setting else True

            preview_segments_setting = db.query(Setting).filter(Setting.key == "preview_segments").first()
            preview_segments = int(preview_segments_setting.value) if preview_segments_setting else 10

            preview_duration_setting = db.query(Setting).filter(Setting.key == "preview_duration").first()
            preview_duration = float(preview_duration_setting.value) if preview_duration_setting else 2.0

            preview_audio = True  # Always include audio

            # First pass: enumerate files
            file_list = []
            for root, _, files in os.walk(task.directory):
                if task.cancel_flag:
                    break
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        file_list.append(os.path.join(root, f))

            if task.cancel_flag:
                task.status = "cancelled"
                return

            task.total = len(file_list)
            task.current = 0

            # Second pass: process
            for full_path in file_list:
                if task.cancel_flag:
                    task.status = "cancelled"
                    break

                task.current_file = full_path

                existing = db.query(Video).filter(Video.path == full_path).first()
                if existing and skip_scanned:
                    has_thumb = bool(existing.thumbnail_path and os.path.exists(existing.thumbnail_path))
                    has_preview = bool(existing.preview_path and os.path.exists(existing.preview_path))

                    if (task.scan_type == "all" and has_thumb and has_preview) or \
                       (task.scan_type == "thumbnail" and has_thumb) or \
                       (task.scan_type == "preview" and has_preview):
                        task.current += 1
                        continue

                print(f"[Task {task.id}] Processing ({task.scan_type}): {full_path}")
                process_video_file(db, full_path, thumb_pct, preview_segments,
                                   preview_duration, preview_audio, task.scan_type)
                task.current += 1

            if not task.cancel_flag:
                task.status = "completed"

        except Exception as e:
            task.status = "error"
            task.error_message = str(e)
            print(f"[Task {task.id}] Error: {e}")
        finally:
            db.close()


# Module-level singleton
task_queue = TaskQueue()
