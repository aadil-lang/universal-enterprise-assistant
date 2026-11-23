import asyncio
import edge_tts

async def main():
    text = "Hi, in this video, I'll walk you through the Universal Enterprise HR and IT Assistant that I've built for Acme Corporation."
    communicate = edge_tts.Communicate(text=text, voice="en-IN-PrabhatNeural")
    await communicate.save("artifacts/test_voice_sample.mp3")
    print("Voice sample saved successfully.")

if __name__ == "__main__":
    asyncio.run(main())
