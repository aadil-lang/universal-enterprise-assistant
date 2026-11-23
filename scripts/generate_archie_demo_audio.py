"""
Audio Generation Script for Archie Product Demo.
Persona: Indian Software Engineer narrator (en-IN-PrabhatNeural)
Archie Voice: Female Indian English (en-IN-NeerjaNeural)
Target Total Duration: ~210-230 seconds (3m 30s - 3m 50s), strictly within the 3-4 minute specification (180s - 240s).
"""

import asyncio
import os
import subprocess
import json
import edge_tts

AUDIO_DIR = os.path.abspath("artifacts/demo/audio_archie")
os.makedirs(AUDIO_DIR, exist_ok=True)

NARRATOR_VOICE = "en-IN-PrabhatNeural"
ARCHIE_VOICE = "en-IN-NeerjaNeural"

# Scenes breakdown with audio segments
# Each segment: (filename_prefix, voice, text, pre_pause_ms, post_pause_ms)
AUDIO_SEGMENTS = [
    # Scene 1: Introduction (Target: ~22s)
    ("s1_01", NARRATOR_VOICE, "Hello everyone. In this demonstration, I will walk you through Archie, an AI-powered HR and IT assistant that I have built.", 400, 600),
    ("s1_02", NARRATOR_VOICE, "The idea is simple: instead of navigating multiple systems or searching through company documents, employees can interact with one assistant using either voice or text.", 300, 1000),

    # Scene 2: Personalized Voice Interaction (Target: ~28s)
    ("s2_01", NARRATOR_VOICE, "Once an employee logs in, Archie recognizes their authenticated identity and greets them personally.", 400, 600),
    ("s2_02", NARRATOR_VOICE, "For example, here I am logged in as Bob. I will simply say, Hey Archie, and the assistant becomes available for a conversation.", 300, 800),
    ("s2_03", ARCHIE_VOICE, "Hey Bob! Good afternoon. How can I help you today?", 500, 1000),

    # Scene 3: Employee Info & Policy Retrieval (Target: ~35s)
    ("s3_01", NARRATOR_VOICE, "Let us ask Archie about the available annual leave balance.", 400, 600),
    ("s3_02", NARRATOR_VOICE, "How much annual leave do I have available?", 300, 800),
    ("s3_03", ARCHIE_VOICE, "You have 8 days of annual leave available out of 25 days accrued.", 600, 1000),
    ("s3_04", NARRATOR_VOICE, "Archie retrieves Bob's actual employee information and presents the complete answer in the chat with full policy citations, while speaking a natural conversational summary.", 400, 600),
    ("s3_05", NARRATOR_VOICE, "Notice that voice and text are not separate conversations. They use the same assistant and the same conversation history.", 300, 1000),

    # Scene 4: Multi-turn Conversation & Text Switching (Target: ~26s)
    ("s4_01", NARRATOR_VOICE, "Archie supports continuous multi-turn conversations, so I do not need to repeat the wake phrase for every question.", 400, 600),
    ("s4_02", NARRATOR_VOICE, "Can I carry forward unused days to next year?", 300, 800),
    ("s4_03", ARCHIE_VOICE, "Yes, you can carry forward up to 5 unused annual leave days into the next calendar year.", 600, 1000),
    ("s4_04", NARRATOR_VOICE, "And if I want to switch back to typing, I can continue right here in the same conversation thread without losing any context.", 400, 1200),

    # Scene 5: Real HR Transaction & Confirmation (Target: ~48s)
    ("s5_01", NARRATOR_VOICE, "Archie can also help employees initiate real HR workflows.", 400, 600),
    ("s5_02", NARRATOR_VOICE, "I want to apply for annual leave from December 10 to December 12, 2026.", 300, 800),
    ("s5_03", ARCHIE_VOICE, "I have prepared your leave request for 3 working days from December 10th to December 12th, 2026. Please review the details on screen and confirm.", 600, 1000),
    ("s5_04", NARRATOR_VOICE, "Before anything is submitted, Archie validates the request against policy and displays the details for review.", 400, 600),
    ("s5_05", NARRATOR_VOICE, "Notice what happens when I say, Yes, submit it.", 300, 600),
    ("s5_06", ARCHIE_VOICE, "Spoken confirmation is not permitted for transactions. Please review the transaction card and click Confirm Submission.", 500, 800),
    ("s5_07", NARRATOR_VOICE, "For an enterprise action, the employee must explicitly review and confirm it using the button on screen.", 400, 600),
    ("s5_08", NARRATOR_VOICE, "Once confirmed, the backend persists the request and returns its actual request status.", 300, 1200),

    # Scene 6: Additional Enterprise Capabilities (Target: ~24s)
    ("s6_01", NARRATOR_VOICE, "The same architecture supports additional workflows, including IT support tickets, reimbursements, HR service requests, equipment requests, and employee contact updates.", 400, 600),
    ("s6_02", NARRATOR_VOICE, "Each follows the same principle: Archie prepares the request, validates it, and waits for explicit confirmation before execution.", 300, 1200),

    # Scene 7: Architecture & Conclusion (Target: ~27s)
    ("s7_01", NARRATOR_VOICE, "Under the hood, Archie uses a shared conversation and orchestration pipeline. It combines company policy retrieval, employee-specific information, and transactional workflows.", 400, 600),
    ("s7_02", NARRATOR_VOICE, "The focus has been on making everyday employee services simpler while maintaining clear authorization boundaries and human control over sensitive actions.", 400, 600),
    ("s7_03", NARRATOR_VOICE, "That is Archie — a conversational HR and IT assistant designed to make employee services more accessible.", 300, 1000),
]

async def synthesize_all():
    segment_files = []
    print("Generating refined audio segments with edge-tts...")
    
    for prefix, voice, text, pre_ms, post_ms in AUDIO_SEGMENTS:
        raw_mp3 = os.path.join(AUDIO_DIR, f"{prefix}_raw.mp3")
        padded_wav = os.path.join(AUDIO_DIR, f"{prefix}.wav")
        
        # Rate: +15% for narrator, +8% for Archie - crisp, natural, professional pacing
        rate = "+15%" if voice == NARRATOR_VOICE else "+8%"
        comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await comm.save(raw_mp3)
        
        filter_str = f"adelay={pre_ms}|{pre_ms},apad=pad_dur={post_ms/1000.0}"
        cmd = [
            "ffmpeg", "-y",
            "-i", raw_mp3,
            "-af", filter_str,
            "-ar", "48000",
            "-ac", "2",
            padded_wav
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        segment_files.append(padded_wav)

    # Concat all segments into master track
    concat_list_file = os.path.join(AUDIO_DIR, "concat_list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in segment_files:
            norm_p = p.replace('\\', '/')
            f.write(f"file '{norm_p}'\n")

    master_wav = os.path.join(AUDIO_DIR, "archie_demo_narration_master.wav")
    master_m4a = os.path.join(AUDIO_DIR, "archie_demo_narration_master.m4a")

    print("\nConcatenating audio into master track...")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_file,
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        master_wav
    ], check=True)

    # Convert to 256k AAC in M4A container (accurate duration container)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", master_wav,
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        master_m4a
    ], check=True)

    # Probe duration accurately
    probe = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,bit_rate",
        "-of", "json",
        master_wav
    ])
    info = json.loads(probe)
    duration = float(info['format']['duration'])
    print(f"\n=======================================================")
    print(f" Master Audio Generated: {master_wav}")
    print(f" Total Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f" Target Duration Window: 180s - 240s (3-4 minutes)")
    print(f" Specification Met: {180 <= duration <= 240}")
    print(f"=======================================================\n")

    # Calculate scene time boundaries for video sync
    scene_boundaries = {}
    current_time = 0.0
    for prefix, voice, text, pre_ms, post_ms in AUDIO_SEGMENTS:
        scene_key = prefix.split("_")[0]
        seg_file = os.path.join(AUDIO_DIR, f"{prefix}.wav")
        seg_probe = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            seg_file
        ])
        seg_dur = float(json.loads(seg_probe)['format']['duration'])
        if scene_key not in scene_boundaries:
            scene_boundaries[scene_key] = {"start": current_time, "duration": 0.0, "segments": []}
        scene_boundaries[scene_key]["duration"] += seg_dur
        scene_boundaries[scene_key]["segments"].append({"prefix": prefix, "start": current_time, "duration": seg_dur})
        current_time += seg_dur

    with open(os.path.join(AUDIO_DIR, "scene_timings.json"), "w", encoding="utf-8") as f:
        json.dump({"total_duration": duration, "scenes": scene_boundaries}, f, indent=2)
    print("Scene timings saved to scene_timings.json:")
    for sc, data in scene_boundaries.items():
        print(f"  {sc}: start={data['start']:.2f}s, duration={data['duration']:.2f}s")

if __name__ == "__main__":
    asyncio.run(synthesize_all())
