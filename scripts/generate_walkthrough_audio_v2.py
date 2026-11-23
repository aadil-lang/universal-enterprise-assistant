import asyncio
import os
import subprocess
import json
import edge_tts

OUTPUT_DIR = os.path.abspath("artifacts/demo/audio_v2")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Using en-IN-PrabhatNeural at +6% rate to fit smoothly inside 3-4 minutes (approx 225-235s)
VOICE = "en-IN-PrabhatNeural"

SCENES = {
    "scene1_intro": (
        "Hi, in this video, I will walk you through the Universal Enterprise H R and I T Assistant that I have built for Acme Corporation. "
        "The idea behind this application is to provide employees with a single conversational interface where they can access company policies, "
        "retrieve their own H R and I T information, and initiate common employee service workflows. "
        "It also supports H R administrators with appropriately authorized access."
    ),
    "scene2_login_policy": (
        "Let us start with the employee experience. I am logging in as Bob Jones, who has standard employee-level access. "
        "The assistant can answer questions using the company's uploaded policy documents rather than relying entirely on general model knowledge. "
        "For example, I am asking about annual vacation entitlement and the carry-forward limit. "
        "The response is grounded in the retrieved company policy, and the supporting source is displayed alongside the answer. "
        "This helps employees understand where the information comes from."
    ),
    "scene3_leave_confirmation": (
        "Beyond answering questions, the assistant can also initiate employee workflows. "
        "Here, I am asking it to create a leave request. It identifies the requested dates, checks the employee's available balance, and prepares a submission for review. "
        "Importantly, it does not immediately submit the request. The employee first receives a confirmation screen with the transaction details. "
        "Only after explicitly confirming does the system submit the request. "
        "We can then retrieve its status through the conversational interface. "
        "This separates the employee's intention from an actual transaction and keeps the employee in control."
    ),
    "scene4_it_ticket": (
        "The same interaction pattern applies to I T support. "
        "An employee can describe an issue conversationally, and the assistant prepares a structured support ticket. "
        "The employee reviews the details and explicitly confirms before the ticket is created. "
        "This makes the experience straightforward for employees while retaining a clear submission boundary."
    ),
    "scene5_reimbursement": (
        "The assistant also supports additional workflows, including reimbursement submissions and H R service requests. "
        "Here, I am submitting an expense reimbursement for an ergonomic chair. "
        "These workflows follow the same review and confirm approach, with policy-aware validation and persistent transaction records."
    ),
    "scene6_hr_admin": (
        "The application also distinguishes between employee and administrator permissions. "
        "An employee can only access their own information, while an authorized H R administrator can perform permitted cross-employee lookups. "
        "Here, Alice queries the leave balance and open tickets for employee E 1 0 2. "
        "These access boundaries are enforced through the backend rather than relying only on what the frontend displays."
    ),
    "scene7_architecture_conclusion": (
        "Under the hood, the application uses a Fast A P I backend, a Next J S frontend, Lang Graph for orchestration, "
        "Postgres for transactional and employee data, and Chroma D B for policy retrieval. "
        "The Fast M C P layer exposes controlled employee information and transactional operations, with authentication, authorization, and explicit confirmation before write operations. "
        "This is a working prototype with the core employee workflows implemented and tested. "
        "Some production hardening work, particularly distributed transaction recovery and secure receipt file storage, remains outside the current implementation. "
        "That concludes our walkthrough. Thank you for watching."
    ),
}

async def generate_scene_audio():
    total_dur = 0.0
    durations = {}
    for scene_id, text in SCENES.items():
        out_path = os.path.join(OUTPUT_DIR, f"{scene_id}.mp3")
        communicate = edge_tts.Communicate(text=text, voice=VOICE, rate="+6%")
        await communicate.save(out_path)
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', out_path]
        out = subprocess.check_output(cmd)
        dur = float(json.loads(out)['format']['duration'])
        durations[scene_id] = round(dur, 2)
        print(f"{scene_id}: {dur:.2f}s")
        total_dur += dur
    print(f"\nTotal Audio Duration: {total_dur:.2f}s ({total_dur/60:.2f} minutes)")
    
    with open(os.path.join(OUTPUT_DIR, "durations.json"), "w") as f:
        json.dump(durations, f, indent=2)

if __name__ == "__main__":
    asyncio.run(generate_scene_audio())
