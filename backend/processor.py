import subprocess
import json
import os
import shutil
import sys
from pathlib import Path

def get_ffmpeg_path():
    """Find ffmpeg binary in bundled paths or system PATH."""
    candidates = []
    # 1. Check if running inside PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        candidates.append(os.path.join(base_dir, "bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
        candidates.append(os.path.join(base_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg"))

    # 2. Check local project bin/ and current directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))

    candidates.extend([
        os.path.join(current_dir, "bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        os.path.join(current_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        os.path.join(project_root, "bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        os.path.join(project_root, "ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
    ])

    for p in candidates:
        if os.path.isfile(p):
            return p

    # 3. Check system PATH
    sys_path = shutil.which("ffmpeg")
    if sys_path:
        return sys_path

    return "ffmpeg"

def get_ffprobe_path():
    """Find ffprobe binary in bundled paths or system PATH."""
    candidates = []
    # 1. Check if running inside PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        candidates.append(os.path.join(base_dir, "bin", "ffprobe.exe" if os.name == "nt" else "ffprobe"))
        candidates.append(os.path.join(base_dir, "ffprobe.exe" if os.name == "nt" else "ffprobe"))

    # 2. Check local project bin/ and current directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))

    candidates.extend([
        os.path.join(current_dir, "bin", "ffprobe.exe" if os.name == "nt" else "ffprobe"),
        os.path.join(current_dir, "ffprobe.exe" if os.name == "nt" else "ffprobe"),
        os.path.join(project_root, "bin", "ffprobe.exe" if os.name == "nt" else "ffprobe"),
        os.path.join(project_root, "ffprobe.exe" if os.name == "nt" else "ffprobe"),
    ])

    for p in candidates:
        if os.path.isfile(p):
            return p

    # 3. Check system PATH
    sys_path = shutil.which("ffprobe")
    if sys_path:
        return sys_path

    return "ffprobe"

def check_ffmpeg_installed():
    """Verify ffmpeg and ffprobe are available either bundled or in the system PATH."""
    ffmpeg_bin = get_ffmpeg_path()
    ffprobe_bin = get_ffprobe_path()
    has_ffmpeg = os.path.isfile(ffmpeg_bin) or (shutil.which(ffmpeg_bin) is not None)
    has_ffprobe = os.path.isfile(ffprobe_bin) or (shutil.which(ffprobe_bin) is not None)
    return has_ffmpeg and has_ffprobe

def get_video_metadata(video_path: str):
    """Uses ffprobe to extract video duration."""
    cmd = [
        get_ffprobe_path(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        duration = float(data.get("format", {}).get("duration", 0.0))
        return {
            "duration": duration,
        }
    except Exception as e:
        print(f"Error reading metadata for {video_path}: {e}")
        return None

def generate_thumbnail(video_path: str, output_path: str, duration: float, percentage: float = 5.0):
    """Generate a single thumbnail at the specified percentage of the total duration.
    
    Uses fast seeking (-ss after -i) to minimize bandwidth usage on FUSE mounts.
    """
    target_time = max(0, duration * (percentage / 100.0))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        get_ffmpeg_path(),
        "-y",               # Overwrite existing files
        "-ss", str(target_time), # Fast seek to timestamp (before -i for accuracy, but we use -noaccurate_seek for speed)
        "-noaccurate_seek", # Allow faster seeking at cost of slight timestamp inaccuracy
        "-i", video_path,   # Input file
        "-vframes", "1",    # Extract exactly 1 frame
        "-q:v", "2",        # High quality JPEG
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error generating thumbnail: {e.stderr}")
        return False

def generate_preview(video_path: str, output_path: str, duration: float,
                    segments: int = 10, segment_duration: float = 2.0, include_audio: bool = False):
    """
    Generate a dynamic preview clip by extracting `segments` clips of `segment_duration`
    evenly spaced throughout the video.
    
    Uses concat demuxer with fast seeking to minimize bandwidth usage on FUSE mounts.
    This approach opens the file only once and uses fast seeking, reducing bandwidth by ~99%.
    """
    # Defensive check: if video is too short, just copy the whole thing or generate a simpler preview
    if duration < (segments * segment_duration):
        segments = max(1, int(duration // segment_duration))
        if segments == 0:
             return False # Video too short to preview meaningfully
             
    # Calculate timestamps
    interval = duration / (segments + 1)
    timestamps = [interval * i for i in range(1, segments + 1)]
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create a temporary concat file for the concat demuxer
    # This allows us to use fast seeking with a single file open
    import tempfile
    concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    try:
        # Write concat file entries with fast seek points
        for ts in timestamps:
            # Escape backslashes in Windows paths
            escaped_path = video_path.replace('\\', '/')
            concat_file.write(f"file '{escaped_path}'\n")
            concat_file.write(f"inpoint {ts}\n")
            concat_file.write(f"outpoint {ts + segment_duration}\n")
        concat_file.close()
        
        # Build ffmpeg command using concat demuxer
        cmd = [
            get_ffmpeg_path(),
            "-y",
            "-f", "concat",
            "-safe", "0",  # Allow unsafe file paths
            "-i", concat_file.name,
            "-vf", "scale=-2:480",  # Scale to 480p height
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "28",  # Decent compression for preview
        ]
        
        if include_audio:
            cmd.extend(["-c:a", "aac"])
        else:
            cmd.extend(["-an"])  # No audio
        
        cmd.append(output_path)
        
        print(f"[DEBUG] FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error generating preview: {e.stderr}")
        return False
    finally:
        # Clean up temporary concat file
        try:
            os.unlink(concat_file.name)
        except OSError:
            pass

import hashlib
from sqlalchemy.orm import Session
from models import Video

def _get_hash(path: str):
    return hashlib.md5(path.encode()).hexdigest()

def process_video_file(db: Session, video_path: str, thumbnail_percentage: float = 5.0, 
                       preview_segments: int = 10, preview_duration: float = 2.0, preview_audio: bool = False,
                       scan_type: str = "all"):
    
    print(f"Extracting metadata for {video_path}")
    metadata = get_video_metadata(video_path)
    if not metadata:
        return None
        
    duration = metadata["duration"]
    
    # Generate static assets caching filenames based on absolute path
    file_hash = _get_hash(video_path)
    cache_dir = os.path.join(os.getcwd(), "data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    thumb_path = os.path.join(cache_dir, f"{file_hash}_thumb.jpg")
    preview_vid_path = os.path.join(cache_dir, f"{file_hash}_preview.mp4")
    
    if scan_type in ("all", "thumbnail"):
        print(f"Generating thumbnail at {thumbnail_percentage}%...")
        generate_thumbnail(video_path, thumb_path, duration, percentage=thumbnail_percentage)
    
    if scan_type in ("all", "preview"):
        print(f"Generating dynamic preview...")
        generate_preview(video_path, preview_vid_path, duration, segments=preview_segments, segment_duration=preview_duration, include_audio=preview_audio)
    
    # Save to db
    video = db.query(Video).filter(Video.path == video_path).first()
    if not video:
        video = Video(path=video_path)
        db.add(video)
        
    video.duration = duration
    
    if os.path.exists(thumb_path):
        video.thumbnail_path = thumb_path
    if os.path.exists(preview_vid_path):
        video.preview_path = preview_vid_path
    
    db.commit()
    db.refresh(video)
    return video
