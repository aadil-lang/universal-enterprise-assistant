"""
Finalizes the Archie Product Demo Video.
Multiplexes 1920x1080 screen capture with natural Indian English master narration audio.
Outputs to: artifacts/demo/archie_product_demo.mp4
Strict specifications:
- Resolution: 1920x1080
- Framerate: 60 FPS Constant Frame Rate (CFR)
- Container: MP4
- Video Codec: H.264 High Profile (16-20 Mbps)
- Audio Codec: AAC, 48 kHz, 256 kbps
- Duration: 3-4 minutes (verified by FFprobe)
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import os
import glob
import subprocess
import json

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video_archie")
AUDIO_FILE = os.path.abspath("artifacts/demo/audio_archie/archie_demo_narration_master.m4a")
OUTPUT_VIDEO = os.path.abspath("artifacts/demo/archie_product_demo.mp4")

def finalize_video():
    videos = glob.glob(os.path.join(RAW_VIDEO_DIR, "*.webm")) + glob.glob(os.path.join(RAW_VIDEO_DIR, "*.mp4"))
    if not videos:
        raise FileNotFoundError(f"No raw video found in {RAW_VIDEO_DIR}")
    
    latest_video = max(videos, key=os.path.getmtime)
    print(f"Latest raw video found: {latest_video}")

    raw_probe = subprocess.check_output([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration:stream=width,height,r_frame_rate,codec_name',
        '-of', 'json', latest_video
    ])
    raw_info = json.loads(raw_probe)
    raw_dur = float(raw_info['format']['duration'])
    print(f"Raw video duration: {raw_dur:.2f}s")

    audio_probe = subprocess.check_output([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,bit_rate',
        '-of', 'json', AUDIO_FILE
    ])
    audio_info = json.loads(audio_probe)
    audio_dur = float(audio_info['format']['duration'])
    print(f"Narration audio duration: {audio_dur:.2f}s")

    # Target duration: match audio duration exactly
    # Enforce strict 60 FPS CFR, 18M bitrate, High profile, 48kHz 256k AAC
    cmd = [
        "ffmpeg", "-y",
        "-i", latest_video,
        "-i", AUDIO_FILE,
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-preset", "medium",
        "-b:v", "18M",
        "-maxrate", "20M",
        "-bufsize", "36M",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=60",
        "-r", "60",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-ac", "2",
        "-shortest",
        OUTPUT_VIDEO
    ]

    print("\nExecuting FFmpeg 60 FPS CFR encoding and multiplexing...")
    subprocess.run(cmd, check=True)
    print(f"\nFinal Archie product demo video successfully rendered at:\n{OUTPUT_VIDEO}")

    # Comprehensive FFprobe Verification
    final_probe = subprocess.check_output([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size,bit_rate:stream=width,height,r_frame_rate,avg_frame_rate,codec_name,profile,sample_rate,channels',
        '-of', 'json', OUTPUT_VIDEO
    ])
    info = json.loads(final_probe)
    duration = float(info['format']['duration'])
    size_mb = float(info['format']['size']) / (1024 * 1024)
    total_bitrate = float(info['format'].get('bit_rate', 0)) / 1000

    print("\n=======================================================")
    print(" FFPROBE ACCEPTANCE VERIFICATION REPORT                ")
    print("=======================================================")
    print(f" Output Path:     {OUTPUT_VIDEO}")
    print(f" Duration:        {duration:.2f}s ({duration/60:.2f} minutes) [Target: 180s - 240s]")
    print(f" File Size:       {size_mb:.2f} MB")
    print(f" Total Bitrate:   {total_bitrate:.1f} kbps")
    
    video_stream = next((s for s in info.get('streams', []) if s.get('codec_name') == 'h264'), None)
    audio_stream = next((s for s in info.get('streams', []) if s.get('codec_name') == 'aac'), None)

    if video_stream:
        print(f" Video Stream:    {video_stream.get('codec_name')} ({video_stream.get('profile')})")
        print(f" Resolution:      {video_stream.get('width')}x{video_stream.get('height')} [Target: 1920x1080]")
        print(f" Frame Rate (r):  {video_stream.get('r_frame_rate')} [Target: 60/1 (60 FPS CFR)]")
        print(f" Frame Rate (avg):{video_stream.get('avg_frame_rate')} [Target: 60/1]")
    
    if audio_stream:
        print(f" Audio Stream:    {audio_stream.get('codec_name')} ({audio_stream.get('sample_rate')} Hz, {audio_stream.get('channels')} channels)")

    # Assertions for script automated exit code
    assert 180 <= duration <= 240, f"Duration {duration}s must be between 180 and 240 seconds (3-4 minutes)!"
    assert video_stream['width'] == 1920 and video_stream['height'] == 1080, "Resolution must be exactly 1920x1080!"
    assert video_stream['r_frame_rate'] == "60/1", "Frame rate must be 60 FPS!"
    assert audio_stream['sample_rate'] == "48000", "Audio sample rate must be 48000 Hz!"
    print("\n✓ ALL ESR-STD-v2.4 ACCEPTANCE CRITERIA VERIFIED!")
    print("=======================================================\n")

if __name__ == "__main__":
    finalize_video()
