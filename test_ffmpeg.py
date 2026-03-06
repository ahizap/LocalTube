import subprocess
import os

test_vid = r"D:\VS Code\mywebsite\test_input.mp4"
if not os.path.exists(test_vid):
    # Try finding one
    for root, dirs, files in os.walk(r"d:\VS Code\mywebsite"):
        for f in files:
            if f.endswith(".mp4") and "cache" not in root and "test_preview" not in f:
                test_vid = os.path.join(root, f)
                break
        if os.path.exists(test_vid): break

print(f"Testing with: {test_vid}")
output_path = "test_preview.mp4"
duration = 60.0 # fake duration
segments = 3
segment_duration = 2.0
include_audio = True

interval = duration / (segments + 1)
timestamps = [interval * i for i in range(1, segments + 1)]

filter_complex = ""
inputs = []

for i, ts in enumerate(timestamps):
    inputs.extend(["-ss", str(ts), "-t", str(segment_duration), "-i", test_vid])
    filter_complex += f"[{i}:v]scale=-2:480,setpts=PTS-STARTPTS[v{i}];"
    if include_audio:
        filter_complex += f"[{i}:a]asetpts=PTS-STARTPTS[a{i}];"
        
concat_inputs = "".join([f"[v{i}]" + (f"[a{i}]" if include_audio else "") for i in range(segments)])
filter_complex += f"{concat_inputs}concat=n={segments}:v=1:a={1 if include_audio else 0}[outv]"
if include_audio:
    filter_complex += "[outa];"
    
cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[outv]"]

if include_audio:
    cmd.extend(["-map", "[outa]", "-c:a", "aac"])
    
cmd.extend([
    "-c:v", "libx264", 
    "-preset", "fast",
    "-crf", "28",
    output_path
])

print("Running command:")
print(" ".join(cmd))

try:
    subprocess.run(cmd, check=True)
    print("Success. Checking for audio stream:")
    os.system(f"ffprobe -v error -show_entries stream=codec_type -of default=nw=1:nk=1 {output_path}")
except subprocess.CalledProcessError as e:
    print("FAILED")
