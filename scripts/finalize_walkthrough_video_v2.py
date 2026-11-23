"""
Finalizes the walkthrough video (v2) by multiplexing the raw screen recording with the refined v2 narration audio.
Outputs high-quality 1920x1080 H.264/AAC MP4 to artifacts/demo/acme_hr_it_assistant_walkthrough.mp4
"""

import os
import glob
import subprocess
import json

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video_v2")
AUDIO_FILE = os.path.abspath("artifacts/demo/narration_v2.mp3")
OUTPUT_VIDEO = os.path.abspath("artifacts/demo/acme_hr_it_assistant_walkthrough.mp4")

def finalize_video():
    videos = glob.glob(os.path.join(RAW_VIDEO_DIR, "*.webm")) + glob.glob(os.path.join(RAW_VIDEO_DIR, "*.mp4"))
    if not videos:
        raise FileNotFoundError(f"No raw video found in {RAW_VIDEO_DIR}")
    
    latest_video = max(videos, key=os.path.getmtime)
    print(f"Latest raw video found: {latest_video}")

    raw_probe = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', latest_video])
    raw_dur = float(json.loads(raw_probe)['format']['duration'])
    print(f"Raw video duration: {raw_dur:.2f}s")

    audio_probe = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', AUDIO_FILE])
    audio_dur = float(json.loads(audio_probe)['format']['duration'])
    print(f"Narration audio duration: {audio_dur:.2f}s")

    cmd = [
        "ffmpeg", "-y",
        "-i", latest_video,
        "-i", AUDIO_FILE,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO
    ]

    print("\nRunning FFmpeg multiplexing...")
    subprocess.run(cmd, check=True)
    print(f"\nFinal product walkthrough video successfully updated at:\n{OUTPUT_VIDEO}")

    final_probe = subprocess.check_output([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name',
        '-of', 'json', OUTPUT_VIDEO
    ])
    info = json.loads(final_probe)
    duration = float(info['format']['duration'])
    size_mb = float(info['format']['size']) / (1024 * 1024)
    print(f"\n--- Final Verification ---")
    print(f"Duration: {duration:.2f}s ({duration/60:.2f} minutes)")
    print(f"File Size: {size_mb:.2f} MB")
    for s in info.get('streams', []):
        print(f"Stream {s.get('codec_name')}: {s.get('width')}x{s.get('height')} @ {s.get('r_frame_rate')}")

if __name__ == "__main__":
    finalize_video()
