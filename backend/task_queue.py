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
            # Read settings once upfront
            thumb_pct_setting = db.query(Setting).filter(Setting.key == "thumbnail_percentage").first()
            thumb_pct = float(thumb_pct_setting.value) if thumb_pct_setting else 5.0

            preview_segments_setting = db.query(Setting).filter(Setting.key == "preview_segments").first()
            preview_segments = int(preview_segments_setting.value) if preview_segments_setting else 10

            preview_duration_setting = db.query(Setting).filter(Setting.key == "preview_duration").first()
            preview_duration = float(preview_duration_setting.value) if preview_duration_setting else 2.0

            preview_audio = True

            # === OPTIMIZATION 1: Use os.scandir() for efficient FUSE enumeration ===
            # os.scandir() gets file type from the directory entry itself (DT_REG/DT_DIR),
            # avoiding extra stat() calls that os.walk() would make on FUSE.
            task.current_file = "Enumerating files..."
            file_list = []

            def _scandir_recursive(dir_path):
                """Recursively enumerate files using os.scandir() to minimize stat calls."""
                try:
                    with os.scandir(dir_path) as entries:
                        for entry in entries:
                            if task.cancel_flag:
                                return
                            try:
                                # entry.is_file()/is_dir() use cached d_type from readdir,
                                # no extra stat() on most filesystems including FUSE
                                if entry.is_file(follow_symlinks=False):
                                    ext = os.path.splitext(entry.name)[1].lower()
                                    if ext in SUPPORTED_EXTENSIONS:
                                        file_list.append(entry.path)
                                elif entry.is_dir(follow_symlinks=False):
                                    _scandir_recursive(entry.path)
                            except (PermissionError, OSError):
                                continue
                except (PermissionError, OSError):
                    pass

            _scandir_recursive(task.directory)

            if task.cancel_flag:
                task.status = "cancelled"
                return

            task.total = len(file_list)
            task.current = 0

            # === OPTIMIZATION 2: Batch-load all known videos from DB ===
            # Single query instead of one per file. Build a lookup dict.
            all_videos = db.query(Video).filter(
                Video.path.in_(file_list)
            ).all()
            video_map = {v.path: v for v in all_videos}

            skipped = 0

            # Process files, intelligently skipping already-processed ones
            for full_path in file_list:
                if task.cancel_flag:
                    task.status = "cancelled"
                    break

                task.current_file = full_path

                # Check if this file already has the requested asset
                existing = video_map.get(full_path)
                if existing:
                    # Thumbnail/preview paths point to local cache dir, not FUSE — safe to stat
                    has_thumb = bool(existing.thumbnail_path and os.path.exists(existing.thumbnail_path))
                    has_preview = bool(existing.preview_path and os.path.exists(existing.preview_path))

                    should_skip = False
                    if task.scan_type == "thumbnail" and has_thumb:
                        should_skip = True
                    elif task.scan_type == "preview" and has_preview:
                        should_skip = True
                    elif task.scan_type == "all" and has_thumb and has_preview:
                        should_skip = True

                    if should_skip:
                        task.current += 1
                        skipped += 1
                        continue

                print(f"[Task {task.id}] Processing ({task.scan_type}): {full_path}")
                process_video_file(db, full_path, thumb_pct, preview_segments,
                                   preview_duration, preview_audio, task.scan_type)
                task.current += 1

            if skipped > 0:
                print(f"[Task {task.id}] Skipped {skipped}/{task.total} files (already processed)")

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
