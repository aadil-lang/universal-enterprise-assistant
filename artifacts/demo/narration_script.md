# Archie Product Demo — Narration Script (Dual Journey: HR Admin + Employee)

**Project:** Universal Enterprise HR & IT Assistant  
**Feature:** Archie — Personalized Conversational Voice Assistant  
**Duration:** 299.07s (4 minutes 59.07 seconds)  
**Resolution:** 1920 × 1080 | 60 FPS CFR  
**Narrator Voice:** `en-IN-PrabhatNeural` (Indian English Software Engineer Persona)  
**Archie Voice:** `en-IN-NeerjaNeural` (Female Indian English Voice)  
**Standard:** ESR-STD-v2.4  

---

## Scene 1: Introduction & Product Vision (0:00 – 0:21 · 21.5s)

- **[0:00 – 0:02]** *Narrator:* "Hello everyone."
- **[0:02 – 0:10]** *Narrator:* "Today, I'd like to show you Archie, an AI-powered enterprise HR and IT assistant that I've built."
- **[0:10 – 0:21]** *Narrator:* "In this walkthrough, we'll explore both sides of the application: the HR Administrator managing company policies, and the employee interacting with Archie through natural voice and text."

---

## Scene 2: HR Administrator Journey — Policy Ingestion & Governance (0:21 – 1:29 · 67.6s)

- **[0:21 – 0:25]** *Narrator:* "We'll begin with the HR Administrator journey."
- **[0:25 – 0:30]** *Narrator:* "Here, I'm logging in as Alice Smith, our HR Administrator."
- **[0:30 – 0:38]** *Narrator:* "Notice the purple HR Admin badge in the header, granting access to administrative capabilities such as policy ingestion."
- **[0:38 – 0:48]** *Narrator:* "When company policies are updated, Alice doesn't need technical support to update the knowledge base. She simply clicks Ingest Document."
- **[0:48 – 0:54]** *Narrator:* "Here, Alice uploads our revised Remote Work Policy in Markdown format."
- **[0:54 – 1:03]** *Narrator:* "Once she clicks Upload and Index, the backend parses the document, creates semantically chunked embeddings, and stores them in ChromaDB."
- **[1:03 – 1:08]** *Narrator:* "We can see the confirmation: six chunks generated and indexed in the knowledge base."
- **[1:08 – 1:15]** *Narrator:* "Alice can test retrieval immediately by asking: 'What are the eligibility requirements for remote work?'"
- **[1:15 – 1:22]** *Narrator:* "Archie retrieves the newly ingested policy and provides an authoritative answer with exact citations."
- **[1:22 – 1:29]** *Narrator:* "Now, let's sign out as Alice and see how this knowledge is delivered to employees through voice."

---

## Scene 3: Employee Journey — Authentication & Voice Activation (1:29 – 2:06 · 37.4s)

- **[1:29 – 1:33]** *Narrator:* "Now, let's switch to the employee experience."
- **[1:33 – 1:38]** *Narrator:* "Here, I'm logging in as Bob Jones, an employee in Engineering."
- **[1:38 – 1:46]** *Narrator:* "Notice that Bob has standard employee permissions. To interact with Archie using voice, I click Enable Voice."
- **[1:46 – 1:53]** *Narrator:* "Archie enters active listening mode, waiting for its wake phrase. I can simply say: 'Hey Archie'."
- **[1:53 – 1:59]** *Archie:* "Hey Bob! Good afternoon. How can I help you today?"
- **[1:59 – 2:06]** *Narrator:* "Archie immediately recognizes the authenticated employee and responds with a warm, personalized greeting."

---

## Scene 4: Employee Policy Retrieval & Multimodal Response (2:06 – 2:45 · 38.5s)

- **[2:06 – 2:11]** *Narrator:* "Let's ask Archie about Bob's leave balance using natural speech."
- **[2:11 – 2:15]** *Narrator:* "How much annual leave do I have available?"
- **[2:15 – 2:21]** *Archie:* "You have 8 days of annual leave available out of 25 days accrued."
- **[2:21 – 2:29]** *Narrator:* "Archie retrieves Bob's live employee record through our MCP tools and presents the complete structured breakdown directly in the chat."
- **[2:29 – 2:38]** *Narrator:* "Notice how Archie displays the full leave metrics and citations on screen, while speaking a concise, conversational version aloud."
- **[2:38 – 2:45]** *Narrator:* "This multimodal design gives the employee hands-free convenience without sacrificing detailed visual data."

---

## Scene 5: Continuous Dialogue & Seamless Modality Switching (2:45 – 3:19 · 34.5s)

- **[2:45 – 2:51]** *Narrator:* "Archie also supports natural follow-up conversations without repeating the wake phrase."
- **[2:51 – 2:55]** *Narrator:* "Can I carry forward unused days to next year?"
- **[2:55 – 3:02]** *Archie:* "Yes, you can carry forward up to 5 unused annual leave days into the next calendar year."
- **[3:02 – 3:11]** *Narrator:* "Archie retains the full conversation context. The employee can also seamlessly switch between speaking and typing in the very same chat thread."
- **[3:11 – 3:19]** *Narrator:* "Here, I type a question about maximum consecutive leave days, and Archie answers immediately in the same continuous session."

---

## Scene 6: Real HR Transaction & Mandatory Human Confirmation (3:19 – 4:27 · 67.7s)

- **[3:19 – 3:25]** *Narrator:* "Beyond informational queries, Archie can also initiate transactional HR workflows."
- **[3:25 – 3:34]** *Narrator:* "Let's apply for annual leave using voice: 'I want to apply for annual leave from December 10 to December 12, 2026.'"
- **[3:34 – 3:46]** *Archie:* "I have prepared your leave request for 3 working days from December 10th to December 12th, 2026. Please review the details on screen and confirm."
- **[3:46 – 3:54]** *Narrator:* "Archie validates Bob's remaining balance, calculates three working days, and prepares a draft transaction card for review."
- **[3:54 – 4:05]** *Narrator:* "Now, notice a critical security safeguard. Even if I say, 'Yes, submit it', Archie will strictly refuse to execute the transaction through voice alone."
- **[4:05 – 4:14]** *Archie:* "Spoken confirmation is not permitted for transactions. Please review the transaction card and click Confirm Submission."
- **[4:14 – 4:27]** *Narrator:* "For sensitive enterprise actions, explicit human confirmation on screen is mandatory. Once I click Confirm Submission, the transaction is executed and persisted in PostgreSQL."

---

## Scene 7: Multi-Domain Enterprise Requests & Architecture Closing (4:27 – 4:59 · 31.9s)

- **[4:27 – 4:33]** *Narrator:* "The same unified assistant also handles IT tickets and multi-department requests."
- **[4:33 – 4:42]** *Narrator:* "When Bob asks for the status of his open requests, Archie displays both his pending leave applications and an active IT VPN ticket."
- **[4:42 – 4:52]** *Narrator:* "Under the hood, Archie connects Next.js 14, FastAPI, LangGraph, PostgreSQL, and ChromaDB into one reliable, enterprise-grade architecture."
- **[4:52 – 4:59]** *Narrator:* "And that's Archie — one assistant, one conversation, smarter employee services."
