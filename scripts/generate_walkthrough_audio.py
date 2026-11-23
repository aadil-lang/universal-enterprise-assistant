import asyncio
import os
import subprocess
import json
import edge_tts

OUTPUT_DIR = os.path.abspath("artifacts/demo/audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICE = "en-IN-PrabhatNeural"

# Carefully timed to land precisely between 3:20 and 3:45 (200-225s total)
SCENES = {
    "scene1_intro": (
        "Hi, in this walkthrough, I'll demonstrate the Universal Enterprise HR and IT Assistant built for Acme Corporation. "
        "The goal is to provide employees with a single conversational interface to explore company policies, "
        "access personal HR and IT records, and execute self-service workflows with explicit confirmation. "
        "It also enforces role-based access for HR administrators."
    ),
    "scene2_login_policy": (
        "Let's begin with the employee experience. I'm logging in as Bob Jones, who has standard employee access. "
        "The assistant answers questions grounded directly in the company's indexed policy documents using retrieval-augmented generation. "
        "For example, let's ask about annual vacation entitlement and carry-forward limits. "
        "The response cites the exact company policy document and active version, giving employees full transparency into the source."
    ),
    "scene3_leave_confirmation": (
        "Beyond policy Q and A, the assistant handles real transactional workflows. "
        "Here, I'm requesting annual leave from December 10 to December 12. "
        "Notice that instead of committing immediately, the assistant computes the requested days, checks available balance, "
        "and presents an interactive Confirmation Card. "
        "The transaction executes only when the employee explicitly clicks Confirm. "
        "Now let's check the status. We can see our confirmed leave request persisted with its actual request identifier."
    ),
    "scene4_it_ticket": (
        "The same interaction model governs IT support requests. "
        "An employee describes an issue conversationally, such as a flickering laptop screen. "
        "The assistant categorizes the issue as Hardware, sets priority, and renders a structured confirmation card. "
        "Upon confirmation, the ticket is persisted in PostgreSQL with a unique IT ticket ID."
    ),
    "scene5_reimbursement": (
        "The assistant also handles expense reimbursements and HR service requests. "
        "Here, I'll submit a claim for an ergonomic chair purchase of 150 dollars. "
        "The assistant validates the expense category, checks against the annual ergonomic stipend policy, and drafts the transaction card for review before submission."
    ),
    "scene6_hr_admin": (
        "Role-based authorization is strictly enforced at the backend. "
        "I'll sign out of Bob's account and log in as Alice Smith, our HR Administrator. "
        "While regular employees can only view their own records, an authorized HR administrator can query cross-employee data. "
        "Alice requests the leave balance and open tickets for employee E102, which the backend safely authorizes and displays."
    ),
    "scene7_architecture_conclusion": (
        "Architecturally, the application is built on a FastAPI backend, a Next.js 14 frontend, LangGraph orchestration, "
        "PostgreSQL 16 for relational and transactional state, and ChromaDB for policy retrieval. "
        "Write operations are exposed through secure FastMCP tools with HMAC signatures and human-in-the-loop confirmation. "
        "All core employee workflows are fully functional and verified. "
        "That concludes our walkthrough. Thank you for watching."
    ),
}

async def generate_scene_audio():
    total_dur = 0.0
    for scene_id, text in SCENES.items():
        out_path = os.path.join(OUTPUT_DIR, f"{scene_id}.mp3")
        communicate = edge_tts.Communicate(text=text, voice=VOICE, rate="+8%")
        await communicate.save(out_path)
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', out_path]
        out = subprocess.check_output(cmd)
        dur = float(json.loads(out)['format']['duration'])
        print(f"{scene_id}: {dur:.2f}s")
        total_dur += dur
    print(f"\nTotal Audio Duration: {total_dur:.2f}s ({total_dur/60:.2f} minutes)")

if __name__ == "__main__":
    asyncio.run(generate_scene_audio())
