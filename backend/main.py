from fastapi import FastAPI, Depends, BackgroundTasks, File, UploadFile, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
import os
import json
from task_queue import task_queue
from fastapi.staticfiles import StaticFiles

# Create DB tables
Base.metadata.create_all(bind=engine)

os.makedirs("cache", exist_ok=True)

app = FastAPI(title="Tube Site API")

app.mount("/cache", StaticFiles(directory="cache"), name="cache")

# Allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def read_root():
    return {"status": "ok"}

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(models.Setting).all()
    # Default settings dict
    settings_dict = {
        "thumbnail_percentage": 5.0,
        "preview_segments": 10,
        "preview_duration": 2.0,
        "preview_audio": True,
        "default_browse_path": "",
        "max_concurrent_tasks": 2
    }
    for s in settings:
        try:
            settings_dict[s.key] = json.loads(s.value)
        except:
            settings_dict[s.key] = s.value # Fallback if not JSON
            
    return settings_dict

@app.post("/api/settings")
def save_setting(key: str, value: str, db: Session = Depends(get_db)):
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = models.Setting(key=key, value=value)
        db.add(setting)
    db.commit()
    return {"status": "ok", "key": key}

@app.post("/api/scan")
def trigger_scan(type: str = "all", directory: str = ""):
    """Submit a scan task to the queue."""
    if not directory:
        return {"status": "error", "message": "No directory specified"}
    task = task_queue.submit(type, directory)
    return {"status": "ok", "task_id": task.id}

@app.get("/api/tasks")
def get_tasks():
    """Returns all tasks and their progress."""
    return task_queue.get_all_tasks()

@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a specific task."""
    success = task_queue.cancel(task_id)
    if success:
        return {"status": "ok", "message": f"Task {task_id} cancellation requested"}
    return {"status": "error", "message": "Task not found"}

@app.post("/api/tasks/clear")
def clear_finished_tasks():
    """Remove completed/cancelled/error tasks."""
    task_queue.clear_finished()
    return {"status": "ok"}

import ctypes

@app.get("/api/fs/list")
def list_directory(path: str = ""):
    """Lists contents of a directory. Returns directories only to build a file explorer."""
    # Handle Windows drives
    is_windows = os.name == 'nt'
    if not path and is_windows:
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if bitmask & 1:
                drives.append({"name": f"{letter}:\\", "path": f"{letter}:\\"})
            bitmask >>= 1
        return {"path": "", "parent": "", "directories": drives, "is_root": True}

    if not path and not is_windows:
        path = "/"
        
    if not os.path.exists(path) or not os.path.isdir(path):
        return {"error": "Path is not a valid directory"}
        
    try:
        items = os.listdir(path)
        directories = []
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                directories.append({"name": item, "path": full_path})
                
        # Sort directories alphabetically
        directories.sort(key=lambda x: x["name"].lower())
        
        parent_path = os.path.dirname(path)
        if parent_path == path: # we're at root
             parent_path = "" if is_windows else "/"
             
        return {
            "path": path,
            "parent": parent_path,
            "directories": directories,
            "is_root": parent_path == ""
        }
    except PermissionError:
        return {"error": "Permission denied"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/videos")
def get_videos(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    videos = db.query(models.Video).order_by(models.Video.created_at.desc()).offset(skip).limit(limit).all()
    # Replace absolute system paths with API served paths for the frontend
    result = []
    for v in videos:
        v_dict = {
            "id": v.id,
            "duration": v.duration,
            "created_at": v.created_at,
            "title": os.path.basename(v.path)
        }
        if v.thumbnail_path:
            v_dict["thumbnail_path"] = f"/cache/{os.path.basename(v.thumbnail_path)}"
        if v.preview_path:
            v_dict["preview_path"] = f"/cache/{os.path.basename(v.preview_path)}"
        result.append(v_dict)
    return result

@app.get("/api/videos/{video_id}")
def get_video_details(video_id: int, db: Session = Depends(get_db)):
    v = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not v:
        return {"error": "Video not found"}
        
    return {
        "id": v.id,
        "path": v.path, # Internal path usually shouldn't be exposed, but we need it here to stream
        "title": os.path.basename(v.path),
        "duration": v.duration,
        "created_at": v.created_at
    }

import mimetypes

@app.get("/api/stream/{video_id}")
def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video or not os.path.exists(video.path):
        return {"error": "Video not found"}
        
    file_path = video.path
    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = "video/mp4" # fallback
        
    range_header = request.headers.get('Range')
    if range_header:
        # Partial request (seeking)
        byte1, byte2 = 0, None
        match = range_header.replace('bytes=', '').split('-')
        byte1 = int(match[0])
        if len(match) > 1 and match[1]:
            byte2 = int(match[1])
        else:
            byte2 = file_size - 1
            
        length = byte2 - byte1 + 1
        
        def file_iterator():
            with open(file_path, "rb") as f:
                f.seek(byte1)
                remaining = length
                chunk_size = 1024 * 1024 # 1 MB chunks
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)
                
        headers = {
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
            'Content-Type': content_type,
        }
        return StreamingResponse(file_iterator(), status_code=206, headers=headers)
        
    # Full request
    return FileResponse(file_path, media_type=content_type)
