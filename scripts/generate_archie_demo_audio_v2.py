"""
Audio Generation Script for Archie Product Demo (v2).
Includes both Employee Journey (Bob Jones) and HR Administrator Journey (Alice Smith).
Persona: Indian Software Engineer narrator (en-IN-PrabhatNeural)
Archie Voice: Female Indian English (en-IN-NeerjaNeural)
Target Total Duration: Exactly 299.0 seconds (4 minutes 59 seconds).
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import asyncio
import os
import subprocess
import json
import edge_tts

AUDIO_DIR = os.path.abspath("artifacts/demo/audio_archie_v2")
os.makedirs(AUDIO_DIR, exist_ok=True)

NARRATOR_VOICE = "en-IN-PrabhatNeural"
ARCHIE_VOICE = "en-IN-NeerjaNeural"

# Target scene durations summing to 299.0 seconds (4:59)
SCENE_TARGETS = {
    "s1": 32.0,  # Intro & Dual-Persona Vision (0:00 - 0:32)
    "s2": 35.0,  # Bob Login & Voice Activation (0:32 - 1:07)
    "s3": 45.0,  # Employee Info & Policy Retrieval (1:07 - 1:52)
    "s4": 40.0,  # Continuous Dialogue & Text Switching (1:52 - 2:32)
    "s5": 60.0,  # Real HR Transaction & Explicit Confirmation (2:32 - 3:32)
    "s6": 53.0,  # HR Administrator Journey: Alice Smith (3:32 - 4:25)
    "s7": 34.0,  # Enterprise Architecture & Conclusion (4:25 - 4:59)
}

# Scene script breakdown
SCENE_SCRIPTS = {
    "s1": [
        ("s1_01", NARRATOR_VOICE, "Hello everyone. In this demonstration, I will walk you through Archie, an AI-powered enterprise HR and IT assistant that I have built for Acme Corporation.", 400, 600),
        ("s1_02", NARRATOR_VOICE, "The vision behind Archie is simple: instead of navigating multiple siloed portals or searching through static documents, employees and administrators interact with a single conversational assistant using either voice or text.", 400, 800),
        ("s1_03", NARRATOR_VOICE, "Today, we will explore both journeys: everyday employee self-service with Bob, and authorized administrative governance with Alice.", 400, 1000),
    ],
    "s2": [
        ("s2_01", NARRATOR_VOICE, "Let us begin with the employee experience. Here, I am logging in as Bob Jones, a senior software engineer.", 400, 600),
        ("s2_02", NARRATOR_VOICE, "Once authenticated, Archie recognizes Bob's identity. I will enable voice mode and speak the wake phrase, Hey Archie.", 400, 800),
        ("s2_03", ARCHIE_VOICE, "Hey Bob! Good afternoon. How can I help you today?", 500, 1000),
        ("s2_04", NARRATOR_VOICE, "Notice how Archie greets Bob personally with the appropriate time of day, ready for natural conversation.", 400, 1000),
    ],
    "s3": [
        ("s3_01", NARRATOR_VOICE, "Let us ask Archie about annual vacation entitlement.", 400, 600),
        ("s3_02", NARRATOR_VOICE, "How much annual leave do I have available?", 300, 800),
        ("s3_03", ARCHIE_VOICE, "You have 8 days of annual leave available out of 25 days accrued.", 600, 1000),
        ("s3_04", NARRATOR_VOICE, "Archie retrieves Bob's authoritative employee record and displays the full metric breakdown and policy citations in the chat, while speaking a concise, natural summary aloud.", 400, 800),
        ("s3_05", NARRATOR_VOICE, "Voice and text share the exact same state machine and message thread.", 300, 1000),
    ],
    "s4": [
        ("s4_01", NARRATOR_VOICE, "Archie supports continuous multi-turn dialogue, so Bob does not need to repeat the wake phrase.", 400, 600),
        ("s4_02", NARRATOR_VOICE, "Can I carry forward unused days to next year?", 300, 800),
        ("s4_03", ARCHIE_VOICE, "Yes, you can carry forward up to 5 unused annual leave days into the next calendar year.", 600, 1000),
        ("s4_04", NARRATOR_VOICE, "And if Bob prefers to type, he can switch to the chat input immediately without losing context.", 400, 800),
        ("s4_05", NARRATOR_VOICE, "Here, he types a question regarding consecutive leave days, and Archie answers within the identical conversation thread.", 300, 1200),
    ],
    "s5": [
        ("s5_01", NARRATOR_VOICE, "Beyond informational queries, Archie initiates real enterprise workflows.", 400, 600),
        ("s5_02", NARRATOR_VOICE, "I want to apply for annual leave from December 10 to December 12, 2026.", 300, 800),
        ("s5_03", ARCHIE_VOICE, "I have prepared your leave request for 3 working days from December 10th to December 12th, 2026. Please review the details on screen and confirm.", 600, 1000),
        ("s5_04", NARRATOR_VOICE, "Archie validates the dates against policy and renders an interactive confirmation card.", 400, 600),
        ("s5_05", NARRATOR_VOICE, "Notice what happens when I attempt to confirm by voice: Yes, submit it.", 300, 600),
        ("s5_06", ARCHIE_VOICE, "Spoken confirmation is not permitted for transactions. Please review the transaction card and click Confirm Submission.", 500, 800),
        ("s5_07", NARRATOR_VOICE, "For safety, enterprise write operations require explicit human interaction on the screen. Let us click Confirm Submission.", 400, 800),
        ("s5_08", NARRATOR_VOICE, "Once clicked, the backend executes the transaction and confirms the persisted request.", 300, 1200),
    ],
    "s6": [
        ("s6_01", NARRATOR_VOICE, "Now, let us examine the HR administrator journey. Bob signs out, and Alice Smith, our HR Director, signs in.", 400, 600),
        ("s6_02", NARRATOR_VOICE, "Alice enables voice mode and greets Archie.", 300, 600),
        ("s6_03", ARCHIE_VOICE, "Hey Alice! Good afternoon. How can I help you today?", 500, 800),
        ("s6_04", NARRATOR_VOICE, "As an HR administrator, Alice has authorized cross-employee access enforced through backend role-based access control.", 400, 600),
        ("s6_05", NARRATOR_VOICE, "What is the leave balance for employee E102?", 300, 800),
        ("s6_06", ARCHIE_VOICE, "For employee E102, Bob Jones has 3 days of annual leave available out of 20 days accrued.", 600, 1000),
        ("s6_07", NARRATOR_VOICE, "Archie uses authorized Model Context Protocol tools to look up Bob's record for Alice, while strictly preventing standard employees from viewing other colleagues' private data.", 400, 1200),
    ],
    "s7": [
        ("s7_01", NARRATOR_VOICE, "Under the hood, Archie is powered by a unified architecture: a Next.js frontend, FastAPI backend, LangGraph orchestration, PostgreSQL persistence, and ChromaDB policy retrieval.", 400, 600),
        ("s7_02", NARRATOR_VOICE, "Every interaction balances natural conversational speed with strict enterprise authorization boundaries.", 400, 600),
        ("s7_03", NARRATOR_VOICE, "That is Archie — One Assistant, One Conversation, Smarter Employee Services. Thank you for watching.", 400, 1200),
    ],
}

async def generate_v2_audio():
    print("Generating refined v2 audio for Employee & HR Admin journeys...")
    scene_wavs = []
    
    for scene_id, segments in SCENE_SCRIPTS.items():
        target_dur = SCENE_TARGETS[scene_id]
        seg_wavs = []
        
        for prefix, voice, text, pre_ms, post_ms in segments:
            raw_mp3 = os.path.join(AUDIO_DIR, f"{prefix}_raw.mp3")
            padded_wav = os.path.join(AUDIO_DIR, f"{prefix}.wav")
            
            rate = "+10%" if voice == NARRATOR_VOICE else "+4%"
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
            print(f"  ✓ {prefix} ({voice}): \"{text[:35]}...\"")

        # Concat segments for this scene
        scene_list = os.path.join(AUDIO_DIR, f"{scene_id}_list.txt")
        with open(scene_list, "w", encoding="utf-8") as f:
            for p in seg_wavs:
                norm_p = p.replace('\\', '/')
                f.write(f"file '{norm_p}'\n")

        raw_scene_wav = os.path.join(AUDIO_DIR, f"{scene_id}_raw.wav")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", scene_list,
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            raw_scene_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Probe duration of raw scene
        probe = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            raw_scene_wav
        ])
        raw_dur = float(json.loads(probe)['format']['duration'])
        print(f"Scene {scene_id}: raw duration = {raw_dur:.2f}s, target = {target_dur:.2f}s")

        # Pad or trim scene precisely to target_dur
        final_scene_wav = os.path.join(AUDIO_DIR, f"{scene_id}_timed.wav")
        if raw_dur < target_dur:
            pad_dur = target_dur - raw_dur
            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_scene_wav,
                "-af", f"apad=pad_dur={pad_dur}",
                "-c:a", "pcm_s16le",
                "-ar", "48000",
                "-ac", "2",
                final_scene_wav
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_scene_wav,
                "-t", str(target_dur),
                "-c:a", "pcm_s16le",
                "-ar", "48000",
                "-ac", "2",
                final_scene_wav
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        scene_wavs.append(final_scene_wav)

    # Concat all timed scenes into master audio
    master_list = os.path.join(AUDIO_DIR, "master_list.txt")
    with open(master_list, "w", encoding="utf-8") as f:
        for p in scene_wavs:
            norm_p = p.replace('\\', '/')
            f.write(f"file '{norm_p}'\n")

    master_wav = os.path.join(AUDIO_DIR, "archie_demo_narration_master_v2.wav")
    master_m4a = os.path.join(AUDIO_DIR, "archie_demo_narration_master_v2.m4a")

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
    print(f" Master Audio v2 Generated: {master_wav}")
    print(f" Total Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f" Target: 299.00 seconds (4:59)")
    print(f" Exact Match: {abs(duration - 299.0) < 0.1}")
    print(f"=======================================================\n")

    # Save timings
    with open(os.path.join(AUDIO_DIR, "scene_timings_v2.json"), "w", encoding="utf-8") as f:
        json.dump({"total_duration": duration, "scenes": SCENE_TARGETS}, f, indent=2)

if __name__ == "__main__":
    asyncio.run(generate_v2_audio())
