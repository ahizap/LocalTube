import os
import glob
from sqlalchemy.orm import Session
from models import Video, Setting
from processor import process_video_file # We will create this
import json
import time

# Global scanning state
is_scanning = False
cancel_scan_flag = False
scan_progress = {
    "status": "idle", # "idle", "scanning", "cancelled", "completed", "error"
    "total": 0,
    "current": 0,
    "current_file": ""
}

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm"}

def get_directories(db: Session):
    setting = db.query(Setting).filter(Setting.key == "directories").first()
    if not setting:
        return []
    try:
        return json.loads(setting.value)
    except:
        return []

def scan_directories(db: Session, scan_type: str = "all"):
    global is_scanning, cancel_scan_flag, scan_progress
    
    if is_scanning:
        return # Already scanning
        
    is_scanning = True
    cancel_scan_flag = False
    scan_progress = {
        "status": "scanning",
        "total": 0,
        "current": 0,
        "current_file": "Initializing..."
    }
    
    try:
        directories = get_directories(db)
        
        # Get settings for processing
        thumbnail_percentage = db.query(Setting).filter(Setting.key == "thumbnail_percentage").first()
        thumb_pct = float(thumbnail_percentage.value) if thumbnail_percentage else 5.0
        
        skip_scanned_setting = db.query(Setting).filter(Setting.key == "skip_scanned").first()
        skip_scanned = skip_scanned_setting.value == "true" if skip_scanned_setting else True
        
        preview_segments_setting = db.query(Setting).filter(Setting.key == "preview_segments").first()
        preview_segments = int(preview_segments_setting.value) if preview_segments_setting else 10
        
        preview_duration_setting = db.query(Setting).filter(Setting.key == "preview_duration").first()
        preview_duration = float(preview_duration_setting.value) if preview_duration_setting else 2.0
        
        # Audio is always included in generated previews.
        # The "preview_audio" setting is frontend-only (controls mute on hover).
        preview_audio = True
    
        # First pass: count total valid files
        total_files = 0
        file_list = []
        for dir_path in directories:
            if not os.path.exists(dir_path):
                continue
                
            for root, _, files in os.walk(dir_path):
                if cancel_scan_flag:
                    break
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        total_files += 1
                        file_list.append(os.path.join(root, file))
        
        if cancel_scan_flag:
            scan_progress["status"] = "cancelled"
            is_scanning = False
            return

        scan_progress["total"] = total_files
        scan_progress["current"] = 0
    
        # Second pass: process files
        for full_path in file_list:
            if cancel_scan_flag:
                scan_progress["status"] = "cancelled"
                break
                
            scan_progress["current_file"] = full_path

            # Check if exists
            existing = db.query(Video).filter(Video.path == full_path).first()
            
            if existing and skip_scanned and scan_type == "all":
                # Only strictly skip if we're doing "all" AND skip_scanned is true.
                # If the user explicitly asks for "thumbnail" or "preview", we should probably 
                # generate them if they don't exist, even if the video DB entry exists.
                # Actually, let's refine: skip if it exists and we already have the requested asset.
                has_thumb = bool(existing.thumbnail_path and os.path.exists(existing.thumbnail_path))
                has_preview = bool(existing.preview_path and os.path.exists(existing.preview_path))
                
                if (scan_type == "all" and has_thumb and has_preview) or \
                   (scan_type == "thumbnail" and has_thumb) or \
                   (scan_type == "preview" and has_preview):
                    scan_progress["current"] += 1
                    continue
                
            print(f"Processing video ({scan_type}): {full_path}")
            process_video_file(db, full_path, thumb_pct, preview_segments, preview_duration, preview_audio, scan_type)
            scan_progress["current"] += 1
            
        if not cancel_scan_flag:
            scan_progress["status"] = "completed"
            
    except Exception as e:
        scan_progress["status"] = "error"
        scan_progress["current_file"] = f"Error: {str(e)}"
        print(f"Error during scan: {e}")
    finally:
        is_scanning = False
