"""
Professional Narration Generator for Archie Product Demo (v2 - No Trimming).
Exact script from Section 4.
Voice: en-IN-PrabhatNeural (Indian English Software Engineer persona).
Archie Voice: en-IN-NeerjaNeural (Female Indian English).
Target Duration: 3:30-4:15 (210s - 255s).
Rate: +16% for fluent, unhurried, natural delivery (~138 words per minute).
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import asyncio
import os
import subprocess
import json
import edge_tts

AUDIO_DIR = os.path.abspath("artifacts/demo/audio_professional")
os.makedirs(AUDIO_DIR, exist_ok=True)

NARRATOR_VOICE = "en-IN-PrabhatNeural"
ARCHIE_VOICE = "en-IN-NeerjaNeural"

SCENE_SEGMENTS = {
    "s1": [
        ("s1_01", NARRATOR_VOICE, "Hello everyone.", 200, 300),
        ("s1_02", NARRATOR_VOICE, "Today, I'd like to show you Archie, an AI-powered HR and IT assistant that I've built.", 250, 450),
        ("s1_03", NARRATOR_VOICE, "The idea behind Archie is quite simple. Employees shouldn't have to navigate multiple systems or search through lengthy policy documents just to get everyday work-related information.", 250, 400),
        ("s1_04", NARRATOR_VOICE, "Instead, they can interact with one assistant, using either voice or text.", 250, 600),
    ],
    "s2": [
        ("s2_01", NARRATOR_VOICE, "Let's start by logging in as an employee.", 250, 350),
        ("s2_02", NARRATOR_VOICE, "Here, I'm logged in as Bob.", 250, 350),
        ("s2_03", NARRATOR_VOICE, "Once voice mode is enabled, I can simply say, 'Hey Archie'.", 250, 500),
        ("s2_04", ARCHIE_VOICE, "Hey Bob! Good afternoon. How can I help you today?", 500, 600),
        ("s2_05", NARRATOR_VOICE, "Archie recognizes the authenticated employee and responds with a personalized greeting.", 250, 600),
    ],
    "s3": [
        ("s3_01", NARRATOR_VOICE, "Let's ask Archie about the employee's available annual leave.", 250, 450),
        ("s3_02", NARRATOR_VOICE, "How much annual leave do I have available?", 250, 600),
        ("s3_03", ARCHIE_VOICE, "You have 8 days of annual leave available out of 25 days accrued.", 500, 700),
        ("s3_04", NARRATOR_VOICE, "Archie retrieves the information from Bob's employee record and presents the complete answer directly in the chat.", 250, 350),
        ("s3_05", NARRATOR_VOICE, "At the same time, it speaks a shorter, more conversational version of that answer.", 250, 350),
        ("s3_06", NARRATOR_VOICE, "So the employee can listen to the response while still having the complete information available on screen.", 250, 350),
        ("s3_07", NARRATOR_VOICE, "This is an important part of the design. Voice and text are simply two ways of interacting with the same assistant.", 250, 600),
    ],
    "s4": [
        ("s4_01", NARRATOR_VOICE, "Archie also supports continuous conversations.", 250, 350),
        ("s4_02", NARRATOR_VOICE, "Can I carry forward unused days to next year?", 250, 500),
        ("s4_03", ARCHIE_VOICE, "Yes, you can carry forward up to 5 unused annual leave days into the next calendar year.", 500, 700),
        ("s4_04", NARRATOR_VOICE, "I can ask a follow-up question without repeating the wake phrase, and Archie retains the context of the conversation.", 250, 350),
        ("s4_05", NARRATOR_VOICE, "I can also switch back to typing whenever I want. The conversation continues in the same chat, without starting a separate session.", 250, 600),
    ],
    "s5": [
        ("s5_01", NARRATOR_VOICE, "Beyond answering questions, Archie can also help employees initiate actual HR and IT workflows.", 250, 350),
        ("s5_02", NARRATOR_VOICE, "For example, here I'm creating a leave request.", 250, 450),
        ("s5_03", NARRATOR_VOICE, "I want to apply for annual leave from December 10 to December 12, 2026.", 250, 600),
        ("s5_04", ARCHIE_VOICE, "I have prepared your leave request for 3 working days from December 10th to December 12th, 2026. Please review the details on screen and confirm.", 500, 700),
        ("s5_05", NARRATOR_VOICE, "Archie checks the request details, validates the available balance, and prepares a draft for review.", 250, 350),
        ("s5_06", NARRATOR_VOICE, "Now, notice something important. Even if I say, 'Yes, submit it', Archie will not execute the transaction through voice alone.", 250, 500),
        ("s5_07", ARCHIE_VOICE, "Spoken confirmation is not permitted for transactions. Please review the transaction card and click Confirm Submission.", 500, 700),
        ("s5_08", NARRATOR_VOICE, "For sensitive enterprise actions, the employee must review the request and explicitly confirm it using the button on the screen.", 250, 350),
        ("s5_09", NARRATOR_VOICE, "Once I confirm, the backend persists the request and returns its actual status.", 250, 600),
    ],
    "s6": [
        ("s6_01", NARRATOR_VOICE, "The same assistant also supports workflows such as IT support tickets, reimbursement requests, HR service requests, equipment requests, and employee contact updates.", 250, 400),
        ("s6_02", NARRATOR_VOICE, "All of these follow the same principle: Archie prepares and validates the request, while the employee remains in control of the final action.", 250, 600),
    ],
    "s7": [
        ("s7_01", NARRATOR_VOICE, "Under the hood, Archie brings together company policy retrieval, employee-specific information, and transactional workflows through one conversational interface.", 250, 400),
        ("s7_02", NARRATOR_VOICE, "My goal with this project was to make everyday employee services simpler, while keeping authorization and human control at the centre of the experience.", 250, 400),
        ("s7_03", NARRATOR_VOICE, "And that's Archie — your conversational HR and IT assistant.", 250, 800),
    ],
}

async def generate_narration():
    print("Generating natural narration with zero clipping...")
    scene_wavs = []
    scene_durations = {}
    
    for scene_id, segments in SCENE_SEGMENTS.items():
        seg_wavs = []
        for prefix, voice, text, pre_ms, post_ms in segments:
            raw_mp3 = os.path.join(AUDIO_DIR, f"{prefix}_raw.mp3")
            padded_wav = os.path.join(AUDIO_DIR, f"{prefix}.wav")
            
            # Rate: +22% for narrator (~140 wpm, clear and conversational), +8% for Archie
            rate = "+22%" if voice == NARRATOR_VOICE else "+8%"
            comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            await comm.save(raw_mp3)
            
            filter_str = f"adelay={pre_ms}|{pre_ms},apad=pad_dur={post_ms/1000.0}"
            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_mp3,
                "-af", filter_str,
                "-ar", "48000",
                "-ac", "2",
                padded_wav
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            seg_wavs.append(padded_wav)

        scene_list = os.path.join(AUDIO_DIR, f"{scene_id}_list.txt")
        with open(scene_list, "w", encoding="utf-8") as f:
            for p in seg_wavs:
                norm_p = p.replace('\\', '/')
                f.write(f"file '{norm_p}'\n")

        final_scene_wav = os.path.join(AUDIO_DIR, f"{scene_id}_timed.wav")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", scene_list,
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            final_scene_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        probe = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            final_scene_wav
        ])
        scene_dur = float(json.loads(probe)['format']['duration'])
        scene_durations[scene_id] = scene_dur
        print(f"Scene {scene_id}: natural complete duration = {scene_dur:.2f}s")
        scene_wavs.append(final_scene_wav)

    # Master track concat
    master_list = os.path.join(AUDIO_DIR, "master_list.txt")
    with open(master_list, "w", encoding="utf-8") as f:
        for p in scene_wavs:
            norm_p = p.replace('\\', '/')
            f.write(f"file '{norm_p}'\n")

    master_wav = os.path.join(AUDIO_DIR, "archie_demo_narration_professional.wav")
    master_m4a = os.path.join(AUDIO_DIR, "archie_demo_narration_professional.m4a")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", master_list,
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        master_wav
    ], check=True)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", master_wav,
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        master_m4a
    ], check=True)

    probe = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        master_wav
    ])
    duration = float(json.loads(probe)['format']['duration'])
    print(f"\n=======================================================")
    print(f" Master Audio Generated: {master_wav}")
    print(f" Total Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f" Target Window: 210s - 255s (3:30 - 4:15)")
    print(f" In Window: {210 <= duration <= 255}")
    print(f"=======================================================\n")

    with open(os.path.join(AUDIO_DIR, "scene_timings.json"), "w", encoding="utf-8") as f:
        json.dump({"total_duration": duration, "scenes": scene_durations}, f, indent=2)

if __name__ == "__main__":
    asyncio.run(generate_narration())
