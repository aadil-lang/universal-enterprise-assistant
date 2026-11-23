# First-Person Engineer Narration Script: Universal Enterprise HR & IT Assistant

**Presenter:** Engineering Lead / Monorepo Author  
**Target Duration:** ~8:45 (8–10 minutes)  
**Style:** Professional, conversational, natural first-person engineer demo (Loom-style)  
**Tone:** Confident, technically informed, candid about architecture decisions and guardrails  

---

## PART 1 — Architecture Introduction (00:00 – 00:35)

*(Visual: Clean architecture overview diagram displayed on screen. Cursor smoothly traces the data flow from left to right: Next.js Frontend → FastAPI Gateway → LangGraph Agent → ChromaDB / FastMCP / PostgreSQL).*

> "Hey everyone. I built this project as a full-stack enterprise HR and IT assistant designed specifically for complex corporate environments like Acme Corporation.
> 
> Let me quickly explain how the architecture fits together before we jump into the browser.
> 
> On the frontend, I used **Next.js 14** with the App Router and TypeScript, styled with Tailwind CSS to keep the interface fast, responsive, and role-aware. 
> 
> The frontend talks to a **FastAPI** orchestration gateway. Under the hood, FastAPI runs a **LangGraph** deterministic state machine that manages the conversational flow. 
> 
> Now, what makes enterprise assistants tricky is that you're dealing with two completely different kinds of information:
> First, unstructured text—like company handbooks, leave policies, and IT guidelines. For that, I integrated **ChromaDB** to perform dense vector retrieval over active policy versions.
> Second, structured relational data—like personal leave balances, assigned hardware, and open IT support tickets. For that, instead of letting an LLM write raw SQL against a database, I integrated **FastMCP**—the Model Context Protocol—to expose controlled, read-only tools that strictly enforce employee boundary isolation.
> Finally, **PostgreSQL** serves as the system of record for authentication, user profiles, and policy document checksum metadata.
> 
> Let's transition into the actual application in Chromium and see how this all comes together."

*(Cursor glides down to switch from the architecture overview to the Chromium browser window displaying the Acme Corporation login interface).*

---

## PART 2 — Application Introduction and Login (00:35 – 01:30)

*(Visual: Clean Chromium window at `http://localhost:3000`. The login card is centered with Acme Corporation branding, corporate subtitle, and synthetic test credentials selector).*

> "So, this is the actual running application. 
> 
> When designing the security and user experience, I wanted two distinct, first-class personas: standard employees and HR administrators. 
> 
> Let's start with the employee workflow. I'll select Bob Jones from our synthetic test accounts. Bob is a Senior Software Engineer in Engineering with employee ID `E102`.
> 
> Notice how the email `bob@acme.com` populates into the form. When I click 'Sign In', the frontend issues a POST request to `/api/v1/auth/login`. 
> 
> Behind the scenes, the FastAPI backend verifies Bob's credentials using cost-12 Bcrypt hashing, confirms his account is active in the database, and issues an HS256 JWT bearer token. It also sets an `HttpOnly` cookie to protect the session against script-based token theft.
> 
> And here we are inside Bob's workspace. 
> 
> Let's look at the interface. Up top in the navigation bar, you can see the active fiscal year badge—`FY 2026`—and Bob's verified identity pill showing his name, employee number `E102`, and role badge `Employee`.
> 
> One important thing to notice here: because Bob is a regular employee, there are zero administrative controls visible. You don't see any document upload buttons or administrative toggles anywhere in the DOM.
> 
> In the main workspace, we have an empty chat state with suggestion chips tailored specifically to employee self-service.
> 
> Now let's explore how the assistant handles different types of employee questions."

---

## PART 3 — Employee Assistant Journey (01:30 – 05:00)

### Journey A: Personal Leave Balance (01:30 – 02:10)
*(Visual: Cursor glides down to the chat input textarea. Types: "How many annual leave days do I currently have available?" Clicks Send).*

> "Let's test structured record retrieval first. 
> 
> I'll ask: *'How many annual leave days do I currently have available?'*
> 
> When I submit this, the request enters the LangGraph agent. The intent classifier analyzes the query and recognizes that Bob is asking for his personal database record. It routes this directly to the MCP execution node.
> 
> The MCP client sends an HMAC-signed request to our FastMCP tool: `get_employee_leave_balances(employee_number='E102')`. 
> 
> And look at the response:
> *'Based on your verified employee record for fiscal year 2026, your annual leave balance is 8.0 available days, with 20.0 accrued days and 10.0 used days.'*
> 
> What I wanted to ensure here is that the assistant isn't hallucinating numbers from general training data or guessing. It fetched Bob's verified balance straight from the employee database."

### Journey B: Company Leave Policy & Grounded Citations (02:10 – 02:50)
*(Visual: Cursor moves to input box, types: "How many days of annual vacation does Acme provide each year?" Clicks Send).*

> "Now, what happens when Bob asks a general company policy question rather than an employee record question?
> 
> Let's ask: *'How many days of annual vacation does Acme provide each year?'*
> 
> This time, the LangGraph classifier identifies this as a `policy` intent. Instead of calling MCP tools, it dispatches the query to ChromaDB.
> 
> ChromaDB retrieves the semantic chunks from the indexed `Acme_Leave_Policy.pdf`. Before using the chunk, our retrieval service cross-checks PostgreSQL to confirm that this document is marked as the active version.
> 
> Look at the answer:
> *'Under Acme Corporation's Leave Policy, full-time employees are entitled to 18 days of paid annual vacation leave per calendar year.'*
> 
> And right below the answer text, notice this emerald citation card:
> `Acme Leave Policy — Section 2: Annual Vacation Leave Accrual and Rollover`.
> 
> This is a key safety requirement: whenever the assistant provides policy guidance, it must cite the exact document and section so employees can verify the source."

### Journey C: Assigned IT Hardware Information (02:50 – 03:30)
*(Visual: Cursor glides down to input box, types: "What laptop has been assigned to me?" Clicks Send).*

> "Now let's switch from HR to IT. Bob wants to know what hardware is assigned to him.
> 
> I'll submit: *'What laptop has been assigned to me?'*
> 
> Again, this is structured employee data, so the agent invokes the `get_employee_assigned_assets` MCP tool.
> 
> The assistant returns:
> *'Based on your employee records, the laptop assigned to you is: Lenovo ThinkPad T14, Asset Tag LT-8821, Serial Number SN-994821.'*
> 
> Notice that the category badge in the top right of the message card dynamically shows `Employee Record` with a sky-blue accent. The user immediately knows whether the answer came from their personal record or a company policy."

### Journey D: IT Support Ticket Tracking (03:30 – 04:00)
*(Visual: Cursor types: "Can you show me my IT support ticket?" Clicks Send).*

> "Let's check Bob's open IT tickets: *'Can you show me my IT support ticket?'*
> 
> The agent invokes `get_employee_it_tickets` for `E102`.
> 
> It retrieves Bob's active support ticket:
> *'Ticket #IT-1042 — Title: VPN connection timeout, Priority: Medium, Status: Open.'*
> 
> Having both HR and IT data in one unified interface means employees don't have to bounce between five different enterprise portals just to check their leave and tickets."

### Journey E: Hybrid Synthesis — Policy Entitlement vs. Personal Balance (04:00 – 04:35)
*(Visual: Cursor types: "How many annual leave days does the company provide, and how many do I currently have available?" Clicks Send).*

> "Now, this is where things get really interesting: hybrid questions.
> 
> Let's ask: *'How many annual leave days does the company provide, and how many do I currently have available?'*
> 
> This question requires two completely independent retrieval pipelines:
> 1. It needs ChromaDB RAG to find the company vacation entitlement (18 days).
> 2. It needs FastMCP to fetch Bob's current available balance (8 days).
> 
> Look at how the assistant answers:
> It clearly breaks the response into two sections:
> First, the company policy: 18 days of paid annual vacation leave per calendar year, citing the leave policy.
> Second, Bob's personal record: 8.0 available days for FY 2026.
> 
> Keeping these two sources clearly distinguished is critical. The system must never confuse an entitlement rule with an employee's remaining balance."

### Journey F: Policy Deep-Dive & Conversational Follow-ups (04:35 – 05:00)
*(Visual: Cursor submits: "And what about carryover for it?" Clicks Send).*

> "Let's also test multi-turn conversational context.
> 
> I'll ask: *'And what about carryover for it?'*
> 
> Notice that Bob didn't mention the words 'annual leave' or 'policy'—he just used the pronoun 'it'. 
> 
> The conversational state machine looks at the previous turn, recognizes that the topic was annual leave, and enriches the intent.
> 
> It returns:
> *'Under Acme Corporation's Leave Policy, a maximum of 5 unused vacation days can be carried over into the following calendar year.'*
> 
> It correctly cited Section 2 of the Leave Policy. The conversational memory worked seamlessly."

---

## PART 4 — HR Administrator Journey & Complete Document Ingestion (05:00 – 07:00)

*(Visual: Cursor navigates to the top-right header, clicks 'Sign Out'. The page returns cleanly to the login card. Cursor selects Alice Smith E101 HR Admin, and signs in).*

> "Now, let's explore the other side of the platform: the HR Administrator experience.
> 
> I'll sign out of Bob's account and log in as Alice Smith. Alice is Acme's HR Director, employee ID `E101`, with the `hr_admin` role.
> 
> As soon as Alice authenticates, look at the top navigation bar:
> The identity pill now displays `Alice Smith (E101)` with a distinct purple `HR Admin` badge. 
> 
> And look right next to it: an **'Ingest Policy Document'** button has appeared. This control is strictly role-gated and completely inaccessible to standard employees.
> 
> Let's test the complete document ingestion lifecycle from a real document on my local PC."

### Step 1 — Local File Selection (05:30 – 06:00)
*(Visual: Cursor clicks 'Ingest Policy Document'. A clean modal overlay appears. Cursor clicks the file selection dropzone. The native Windows file picker dialog opens. Cursor navigates to local folder `data/fixtures/` and selects `Acme_Remote_Work_Policy.md`).*

> "When Alice clicks 'Ingest Policy Document', this administrative modal opens. 
> 
> The pipeline supports three core enterprise formats: PDF, Microsoft Word DOCX, and Markdown.
> 
> When I click on the file drop zone, it opens my native Windows file explorer. I can navigate directly into my local project directory on my computer and select a policy document—in this case, our remote work guidelines.
> 
> The file name and size appear immediately in the interface, and I can assign the policy title and category."

### Step 2 — Ingestion Pipeline Processing & Chunking (06:00 – 06:30)
*(Visual: Cursor clicks 'Upload & Ingest'. A processing spinner activates with real-time status).*

> "When I click 'Upload & Ingest', here is what happens under the hood:
> 1. **File Validation:** The FastAPI endpoint checks the MIME type, file extension, and magic bytes. It enforces a strict 25 MB ceiling and rejects corrupted or empty files.
> 2. **Text Extraction:** Specialized extractors parse headings, paragraphs, and lists while preserving semantic section boundaries.
> 3. **Chunking & Hashing:** The document is broken into 800-character chunks with a 150-character overlap. Each chunk receives a SHA-256 content hash.
> 4. **Embedding Generation:** Sentence-transformers generate dense embeddings for each chunk.
> 5. **ChromaDB & Postgres Registration:** Vectors are written to ChromaDB, and document metadata—including the authoritative checksum—is recorded in PostgreSQL.
> 
> And there's our emerald success banner: *'Document successfully ingested: 6 chunks indexed into active policy vector collection.'*"

### Step 3 — Verification via Assistant Query (06:30 – 07:00)
*(Visual: Cursor closes modal, logs out of Alice, logs back in as Bob Jones E102. Cursor asks: "What is the ergonomic stipend for remote employees?").*

> "Now let's verify that the newly ingested document is immediately searchable and grounded.
> 
> I'll log out of Alice and sign back in as Bob Jones.
> 
> Let's ask: *'What is the ergonomic stipend for remote employees?'*
> 
> The assistant searches ChromaDB, retrieves the newly indexed chunk from Section 3 of the Remote Work Policy, and answers:
> *'Eligible remote employees are provided a one-time ergonomic home office stipend of $300 [Acme Remote Work Policy, 3. Home-Office Ergonomic Stipend].'*
> 
> That proves the full round-trip: from a file on my local computer, through the validation and ingestion pipeline, into the vector database, and immediately queryable with verifiable citations."

---

## PART 5 — Security and Engineering Decisions (07:00 – 08:30)

*(Visual: Browser transitions to a clean security overview diagram showing isolation boundaries, role-based access rules, and prompt injection defense).*

> "Before we wrap up, I want to highlight several important engineering and security decisions that went into this monorepo.
> 
> ### 1. Read-Only MCP Boundary
> The FastMCP tools are intentionally **read-only**. The assistant can inspect leave balances and tickets, but it possesses zero tools to create, modify, or delete database records. This completely prevents catastrophic tool-use side effects.
> 
> ### 2. Employee Peer Isolation
> Standard employees can never access records belonging to their peers. If Bob asks for Carol's leave balance (`E103`), the MCP client compares Bob's authenticated token claims with the requested employee ID. If they don't match, access is immediately denied.
> 
> ### 3. Internal HMAC Communication
> The API gateway and the MCP server communicate using internal HMAC-SHA256 request signing. Even if someone were inside the container network, they cannot invoke MCP tools without the shared internal secret.
> 
> ### 4. Prompt Injection & Untrusted Data Isolation
> When retrieved policy text is passed to the LLM, it is strictly encapsulated within XML-style boundary delimiters. In our automated test suite, we threw 14 adversarial prompt injection attacks at the assistant—including 'ignore previous instructions' and system prompt extraction. Every single injection was intercepted and refused by our pre-flight guardrails.
> 
> ### 5. HttpOnly Cookie Security
> Authentication tokens are delivered as secure `HttpOnly` cookies, preventing cross-site scripting (XSS) attacks from stealing user credentials."

---

## PART 6 — Closing (08:30 – 08:55)

*(Visual: Returns to the clean, active Acme HR & IT Assistant workspace with the Bob Jones chat history).*

> "So, that's the complete walkthrough of the Acme Universal Enterprise HR & IT Assistant.
> 
> My goal with this project was to bridge two worlds: conversational AI with semantic document search, and deterministic enterprise database access with zero hallucination and strict role-based security.
> 
> By combining Next.js, FastAPI, LangGraph, ChromaDB, and FastMCP, the system delivers grounded, citeable answers in milliseconds while keeping sensitive employee records safe.
> 
> All code, test suites, and documentation are available in the repository.
> 
> Thanks for watching, and I look forward to your questions!"

*(Video fades out cleanly to an end screen).*
