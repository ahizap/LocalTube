import subprocess
import json
import os
import shutil
from pathlib import Path

def check_ffmpeg_installed():
    """Verify ffmpeg and ffprobe are available in the system PATH."""
    has_ffmpeg = shutil.which("ffmpeg") is not None
    has_ffprobe = shutil.which("ffprobe") is not None
    return has_ffmpeg and has_ffprobe

def get_video_metadata(video_path: str):
    """Uses ffprobe to extract video duration."""
    cmd = [
        "ffprobe",
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
    """Generate a single thumbnail at the specified percentage of the total duration."""
    target_time = max(0, duration * (percentage / 100.0))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite existing files
        "-ss", str(target_time), # Seek to timestamp
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
    
    # We will use a complex filtergraph to extract and concatenate segments in one command
    filter_complex = ""
    inputs = []
    
    for i, ts in enumerate(timestamps):
        inputs.extend(["-ss", str(ts), "-t", str(segment_duration), "-i", video_path])
        filter_complex += f"[{i}:v]scale=-2:480,setpts=PTS-STARTPTS[v{i}];"
        if include_audio:
            filter_complex += f"[{i}:a]asetpts=PTS-STARTPTS[a{i}];"
            
    # Concatenate the filtered inputs
    concat_inputs = "".join([f"[v{i}]" + (f"[a{i}]" if include_audio else "") for i in range(segments)])
    if include_audio:
        filter_complex += f"{concat_inputs}concat=n={segments}:v=1:a=1[outv][outa]"
    else:
        filter_complex += f"{concat_inputs}concat=n={segments}:v=1:a=0[outv]"
        
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[outv]"]
    
    if include_audio:
        cmd.extend(["-map", "[outa]", "-c:a", "aac"])
        
    cmd.extend([
        "-c:v", "libx264", 
        "-preset", "slow",
        "-crf", "28", # Decent compression for preview
        output_path
    ])
    
    print(f"[DEBUG] FFmpeg command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error generating preview: {e.stderr}")
        return False

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
