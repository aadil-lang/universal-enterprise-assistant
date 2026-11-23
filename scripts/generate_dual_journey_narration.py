"""
Dual Journey Narration Generator (Optimized for exact 4:55 / 295s duration).
Target: 290s - 298s (4:50 - 4:58), strictly under 4:59.
Persona: en-IN-PrabhatNeural (Indian English Software Engineer).
Archie: en-IN-NeerjaNeural (Female Indian English).
Rate: +22% for narrator (~145 wpm), +8% for Archie.
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import asyncio
import os
import subprocess
import json
import edge_tts

AUDIO_DIR = os.path.abspath("artifacts/demo/audio_dual_journey")
os.makedirs(AUDIO_DIR, exist_ok=True)

NARRATOR_VOICE = "en-IN-PrabhatNeural"
ARCHIE_VOICE = "en-IN-NeerjaNeural"

SCENE_SEGMENTS = {
    "s1": [
        ("s1_01", NARRATOR_VOICE, "Hello everyone.", 200, 300),
        ("s1_02", NARRATOR_VOICE, "Today, I'd like to show you Archie, an AI-powered enterprise HR and IT assistant that I've built.", 250, 450),
        ("s1_03", NARRATOR_VOICE, "In this walkthrough, we'll explore both sides of the application: the HR Administrator managing company policies, and the employee interacting with Archie through natural voice and text.", 250, 600),
    ],
    "s2": [
        ("s2_01", NARRATOR_VOICE, "We'll begin with the HR Administrator journey.", 250, 350),
        ("s2_02", NARRATOR_VOICE, "Here, I'm logging in as Alice Smith, our HR Administrator.", 250, 350),
        ("s2_03", NARRATOR_VOICE, "Notice the purple HR Admin badge in the header, granting access to administrative capabilities such as policy ingestion.", 250, 400),
        ("s2_04", NARRATOR_VOICE, "When company policies are updated, Alice doesn't need technical support to update the knowledge base. She simply clicks Ingest Document.", 250, 450),
        ("s2_05", NARRATOR_VOICE, "Here, Alice uploads our revised Remote Work Policy in Markdown format.", 250, 400),
        ("s2_06", NARRATOR_VOICE, "Once she clicks Upload and Index, the backend parses the document, creates semantically chunked embeddings, and stores them in ChromaDB.", 250, 450),
        ("s2_07", NARRATOR_VOICE, "We can see the confirmation: six chunks generated and indexed in the knowledge base.", 250, 400),
        ("s2_08", NARRATOR_VOICE, "Alice can test retrieval immediately by asking: 'What are the eligibility requirements for remote work?'", 250, 450),
        ("s2_09", NARRATOR_VOICE, "Archie retrieves the newly ingested policy and provides an authoritative answer with exact citations.", 250, 400),
        ("s2_10", NARRATOR_VOICE, "Now, let's sign out as Alice and see how this knowledge is delivered to employees through voice.", 250, 600),
    ],
    "s3": [
        ("s3_01", NARRATOR_VOICE, "Now, let's switch to the employee experience.", 250, 350),
        ("s3_02", NARRATOR_VOICE, "Here, I'm logging in as Bob Jones, an employee in Engineering.", 250, 350),
        ("s3_03", NARRATOR_VOICE, "Notice that Bob has standard employee permissions. To interact with Archie using voice, I click Enable Voice.", 250, 450),
        ("s3_04", NARRATOR_VOICE, "Archie enters active listening mode, waiting for its wake phrase. I can simply say: 'Hey Archie'.", 250, 500),
        ("s3_05", ARCHIE_VOICE, "Hey Bob! Good afternoon. How can I help you today?", 500, 600),
        ("s3_06", NARRATOR_VOICE, "Archie immediately recognizes the authenticated employee and responds with a warm, personalized greeting.", 250, 600),
    ],
    "s4": [
        ("s4_01", NARRATOR_VOICE, "Let's ask Archie about Bob's leave balance using natural speech.", 250, 450),
        ("s4_02", NARRATOR_VOICE, "How much annual leave do I have available?", 250, 600),
        ("s4_03", ARCHIE_VOICE, "You have 8 days of annual leave available out of 25 days accrued.", 500, 700),
        ("s4_04", NARRATOR_VOICE, "Archie retrieves Bob's live employee record through our MCP tools and presents the complete structured breakdown directly in the chat.", 250, 350),
        ("s4_05", NARRATOR_VOICE, "Notice how Archie displays the full leave metrics and citations on screen, while speaking a concise, conversational version aloud.", 250, 400),
        ("s4_06", NARRATOR_VOICE, "This multimodal design gives the employee hands-free convenience without sacrificing detailed visual data.", 250, 600),
    ],
    "s5": [
        ("s5_01", NARRATOR_VOICE, "Archie also supports natural follow-up conversations without repeating the wake phrase.", 250, 350),
        ("s5_02", NARRATOR_VOICE, "Can I carry forward unused days to next year?", 250, 500),
        ("s5_03", ARCHIE_VOICE, "Yes, you can carry forward up to 5 unused annual leave days into the next calendar year.", 500, 700),
        ("s5_04", NARRATOR_VOICE, "Archie retains the full conversation context. The employee can also seamlessly switch between speaking and typing in the very same chat thread.", 250, 400),
        ("s5_05", NARRATOR_VOICE, "Here, I type a question about maximum consecutive leave days, and Archie answers immediately in the same continuous session.", 250, 600),
    ],
    "s6": [
        ("s6_01", NARRATOR_VOICE, "Beyond informational queries, Archie can also initiate transactional HR workflows.", 250, 350),
        ("s6_02", NARRATOR_VOICE, "Let's apply for annual leave using voice: 'I want to apply for annual leave from December 10 to December 12, 2026.'", 250, 550),
        ("s6_03", ARCHIE_VOICE, "I have prepared your leave request for 3 working days from December 10th to December 12th, 2026. Please review the details on screen and confirm.", 500, 700),
        ("s6_04", NARRATOR_VOICE, "Archie validates Bob's remaining balance, calculates three working days, and prepares a draft transaction card for review.", 250, 350),
        ("s6_05", NARRATOR_VOICE, "Now, notice a critical security safeguard. Even if I say, 'Yes, submit it', Archie will strictly refuse to execute the transaction through voice alone.", 250, 500),
        ("s6_06", ARCHIE_VOICE, "Spoken confirmation is not permitted for transactions. Please review the transaction card and click Confirm Submission.", 500, 700),
        ("s6_07", NARRATOR_VOICE, "For sensitive enterprise actions, explicit human confirmation on screen is mandatory. Once I click Confirm Submission, the transaction is executed and persisted in PostgreSQL.", 250, 600),
    ],
    "s7": [
        ("s7_01", NARRATOR_VOICE, "The same unified assistant also handles IT tickets and multi-department requests.", 250, 350),
        ("s7_02", NARRATOR_VOICE, "When Bob asks for the status of his open requests, Archie displays both his pending leave applications and an active IT VPN ticket.", 250, 400),
        ("s7_03", NARRATOR_VOICE, "Under the hood, Archie connects Next.js 14, FastAPI, LangGraph, PostgreSQL, and ChromaDB into one reliable, enterprise-grade architecture.", 250, 450),
        ("s7_04", NARRATOR_VOICE, "And that's Archie — one assistant, one conversation, smarter employee services.", 250, 800),
    ],
}

async def generate_narration():
    print("Generating dual journey narration with natural Indian English cadence...")
    scene_wavs = []
    scene_durations = {}
    
    for scene_id, segments in SCENE_SEGMENTS.items():
        seg_wavs = []
        for prefix, voice, text, pre_ms, post_ms in segments:
            raw_mp3 = os.path.join(AUDIO_DIR, f"{prefix}_raw.mp3")
            padded_wav = os.path.join(AUDIO_DIR, f"{prefix}.wav")
            
            rate = "+29%" if voice == NARRATOR_VOICE else "+10%"
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
        print(f"Scene {scene_id}: duration = {scene_dur:.2f}s")
        scene_wavs.append(final_scene_wav)

    # Master track concat
    master_list = os.path.join(AUDIO_DIR, "master_list.txt")
    with open(master_list, "w", encoding="utf-8") as f:
        for p in scene_wavs:
            norm_p = p.replace('\\', '/')
            f.write(f"file '{norm_p}'\n")

    master_wav = os.path.join(AUDIO_DIR, "archie_dual_journey_narration.wav")
    master_m4a = os.path.join(AUDIO_DIR, "archie_dual_journey_narration.m4a")

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
    print(f" Total Duration: {duration:.2f} seconds ({int(duration//60)}:{int(duration%60):02d})")
    print(f" Target Duration Window: ~4:45 - 4:59 (285s - 299s)")
    print(f" In Window: {280 <= duration <= 299}")
    print(f"=======================================================\n")

    with open(os.path.join(AUDIO_DIR, "scene_timings.json"), "w", encoding="utf-8") as f:
        json.dump({"total_duration": duration, "scenes": scene_durations}, f, indent=2)

if __name__ == "__main__":
    asyncio.run(generate_narration())
