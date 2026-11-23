import os
import subprocess

audio_dir = os.path.abspath("artifacts/demo/audio")
output_audio = os.path.abspath("artifacts/demo/narration_full.mp3")

files = [
    "scene1_intro.mp3",
    "scene2_login_policy.mp3",
    "scene3_leave_confirmation.mp3",
    "scene4_it_ticket.mp3",
    "scene5_reimbursement.mp3",
    "scene6_hr_admin.mp3",
    "scene7_architecture_conclusion.mp3"
]

list_file = os.path.join(audio_dir, "concat_list.txt")
with open(list_file, "w") as f:
    for f_name in files:
        f.write(f"file '{os.path.join(audio_dir, f_name)}'\n")

cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c", "copy",
    output_audio
]

subprocess.run(cmd, check=True)
print(f"Concatenated audio saved to: {output_audio}")

# Verify duration
import json
out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', output_audio])
dur = float(json.loads(out)['format']['duration'])
print(f"Total Combined Narration Duration: {dur:.2f}s ({dur/60:.2f} minutes)")
