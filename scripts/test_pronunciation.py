"""
Test pronunciation of key entities with Indian English voice (en-IN-PrabhatNeural).
Standard: ESR-STD-v2.4
Checks:
- Alice ("AL-iss")
- Archie ("AR-chee")
- Bob, Carol, David, Acme
- LangGraph, ChromaDB, PostgreSQL, API, AI, HR, IT
"""

import asyncio
import os
import edge_tts

OUTPUT_DIR = os.path.abspath("artifacts/demo/test_pronunciation")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICE = "en-IN-PrabhatNeural"

TEST_WORDS = [
    ("alice_default", "Alice"),
    ("alice_phonetic", "Alliss"),
    ("alice_sentence", "Here is Alice, our HR Director."),
    ("archie", "Archie"),
    ("bob", "Bob"),
    ("carol", "Carol"),
    ("david", "David"),
    ("acme", "Acme"),
    ("technical", "LangGraph, ChromaDB, and PostgreSQL."),
]

async def test_all():
    for name, text in TEST_WORDS:
        out_path = os.path.join(OUTPUT_DIR, f"{name}.mp3")
        comm = edge_tts.Communicate(text=text, voice=VOICE, rate="+0%")
        await comm.save(out_path)
        print(f"Generated: {name}.mp3 -> '{text}'")

if __name__ == "__main__":
    asyncio.run(test_all())
