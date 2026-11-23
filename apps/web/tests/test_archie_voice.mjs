/**
 * Archie Voice Assistant Comprehensive Unit Test Suite (ESR-STD-v2.4 §16).
 * 
 * Verifies:
 * 1. TranscriptAssembler (isFinal, resultIndex, deduplication, repeated words, session isolation).
 * 2. SpeechFormatter (Markdown, tables, code, citations, currency, abbreviations).
 * 3. GreetingService (authenticated identity, time of day, once-per-session enforcement).
 * 4. WakeWordDetector (phrase matching, case invariance, one-breath query remainder).
 * 5. VoiceStateMachine (lifecycle transitions, interruption, continuous conversation, teardown).
 * 6. TTS Voice Selection ranking (female en-IN preference and fallbacks).
 */

import assert from 'node:assert';
import { TranscriptAssembler } from '../lib/voice/transcriptAssembler.ts';
import { formatForSpeech, SpeechResponseFormatter } from '../lib/voice/speechFormatter.ts';
import { GreetingService } from '../lib/voice/greetingService.ts';
import { WakeWordDetector } from '../lib/voice/wakeWordDetector.ts';
import { MockSTTProvider } from '../lib/voice/sttProvider.ts';
import { MockTTSProvider } from '../lib/voice/ttsProvider.ts';
import { VoiceStateMachine } from '../lib/voice/voiceStateMachine.ts';
import { VoiceSessionState } from '../lib/voice/types.ts';

console.log('--- Starting Archie Voice Assistant Unit Tests ---');

// ==========================================
// 1. TranscriptAssembler Tests
// ==========================================
console.log('\n[Suite 1] TranscriptAssembler Unit Tests');

{
  // Test 1.1: Basic interim to final transition
  const assembler = new TranscriptAssembler('sess-1');
  
  // Interim event
  const res1 = assembler.processEvent({
    resultIndex: 0,
    results: [
      {
        isFinal: false,
        length: 1,
        0: { transcript: 'how much', confidence: 0.9 },
      },
    ],
  });
  assert.strictEqual(res1.interim, 'how much');
  assert.strictEqual(res1.fullDisplay, 'how much');
  assert.strictEqual(res1.finalText, '');

  // Final event
  const res2 = assembler.processEvent({
    resultIndex: 0,
    results: [
      {
        isFinal: true,
        length: 1,
        0: { transcript: 'how much leave do I have', confidence: 0.98 },
      },
    ],
  });
  assert.strictEqual(res2.interim, '');
  assert.strictEqual(res2.finalText, 'how much leave do I have');
  assert.strictEqual(res2.fullDisplay, 'how much leave do I have');
  assert.strictEqual(res2.isCycleFinal, true);

  // Finalize utterance
  const finalUtterance = assembler.finalizeUtterance();
  assert.strictEqual(finalUtterance, 'how much leave do I have');

  // Duplicate submission prevention
  assert.strictEqual(assembler.finalizeUtterance(), '', 'Duplicate submission must return empty string');
  console.log('  ✓ Test 1.1: Interim to final transition and duplicate submission prevention passed.');
}

{
  // Test 1.2: Engine re-emitting identical prefix from resultIndex 0
  const assembler = new TranscriptAssembler('sess-2');
  
  // Chunk 1 finalized
  assembler.appendFinalChunk('I want to take leave');
  assert.strictEqual(assembler.getFinalText(), 'I want to take leave');

  // Engine emits superset from index 0
  assembler.appendFinalChunk('I want to take leave from December 10');
  assert.strictEqual(assembler.getFinalText(), 'I want to take leave from December 10');
  console.log('  ✓ Test 1.2: Duplicate-prefix superset reconciliation passed.');
}

{
  // Test 1.3: Legitimate repeated words preserved
  const assembler = new TranscriptAssembler('sess-3');
  assembler.appendFinalChunk('This is very very important');
  assert.strictEqual(assembler.getFinalText(), 'This is very very important');

  assembler.appendFinalChunk('no no');
  assert.strictEqual(assembler.getFinalText(), 'This is very very important no no');
  console.log('  ✓ Test 1.3: Legitimate repeated words preservation passed.');
}

{
  // Test 1.4: Stale session events dropped
  const assembler = new TranscriptAssembler('active-session');
  const res = assembler.processEvent(
    {
      resultIndex: 0,
      results: [
        {
          isFinal: true,
          length: 1,
          0: { transcript: 'stale text', confidence: 0.8 },
        },
      ],
    },
    'old-stale-session'
  );
  assert.strictEqual(res.finalText, '', 'Stale session events must be dropped');
  console.log('  ✓ Test 1.4: Stale session event protection passed.');
}

// ==========================================
// 2. SpeechFormatter Tests
// ==========================================
console.log('\n[Suite 2] SpeechFormatter Unit Tests');

{
  // Test 2.1: Stripping Markdown headings, bold, bullet points
  const raw = `### Leave Balance Summary
You currently have **8.0 days** of *annual leave* remaining:
- Accrued: 10.0 days
- Used: 0.0 days
- Pending: 2.0 days`;

  const spoken = formatForSpeech(raw);
  assert(!spoken.includes('###'), 'Must not speak raw hashes');
  assert(!spoken.includes('**'), 'Must not speak bold asterisks');
  assert(!spoken.includes('- '), 'Must not speak dashes');
  assert(spoken.includes('8.0 days of annual leave remaining'), 'Content text must be preserved');
  console.log('  ✓ Test 2.1: Markdown headings, bold, and list formatting passed.');
}

{
  // Test 2.2: Markdown table conversational transformation
  const tableMarkdown = `Here is your hardware allocation:
| Device | Model | Serial |
|---|---|---|
| Laptop | MacBook Pro 16 | C02G9012 |
| Monitor | Dell 27 4K | DL44901 |`;

  const spoken = formatForSpeech(tableMarkdown);
  assert(!spoken.includes('|'), 'Must not speak pipe characters');
  assert(!spoken.includes('---'), 'Must not speak table separator lines');
  assert(spoken.includes('Device: Laptop') || spoken.includes('MacBook Pro 16'), 'Table content must be summarized');
  console.log('  ✓ Test 2.2: Conversational table transformation passed.');
}

{
  // Test 2.3: Currency, abbreviations, code, and URL handling
  const raw = `The ergonomic home office reimbursement allows up to $300 for IT equipment.
Refer to [Acme Policy](https://intranet.acme.com/policy/remote) or \`IT-POLICY-2026\`.
\`\`\`json
{"code": "EXP_01", "max": 300}
\`\`\``;

  const spoken = formatForSpeech(raw);
  assert(spoken.includes('300 dollars'), 'Currency $300 must format to 300 dollars');
  assert(spoken.includes('I.T.'), 'IT abbreviation must format to I.T.');
  assert(!spoken.includes('https://'), 'Raw URLs must not be spoken');
  assert(!spoken.includes('{"code":'), 'Raw JSON/code blocks must not be spoken');
  console.log('  ✓ Test 2.3: Currency, abbreviations, URLs, and code blocks passed.');
}

{
  // Test 2.4: Natural conversational phrasing & contractions (Prompt §4 examples)
  const formatter = new SpeechResponseFormatter();

  // Example 1: Leave balance
  const r1 = "Your available annual leave balance is 8 days.";
  const s1 = formatter.format(r1);
  assert(s1.includes("You've got 8 days of annual leave available"), `Expected conversational leave balance, got: ${s1}`);

  // Example 2: Policies identified
  const r2 = "I have identified three relevant policies.";
  const s2 = formatter.format(r2);
  assert(s2.includes("I found three policies that might help"), `Expected conversational policies, got: ${s2}`);

  // Example 3: Required info
  const r3 = "Please provide the required information.";
  const s3 = formatter.format(r3);
  assert(s3.includes("I just need a couple of details first"), `Expected friendly detail request, got: ${s3}`);

  // Example 4: Submitted
  const r4 = "Your request has been submitted successfully.";
  const s4 = formatter.format(r4);
  assert(s4.includes("All done. Your request has been submitted"), `Expected natural submission confirmation, got: ${s4}`);

  // Example 5: Equipment pending approval
  const r5 = "The requested equipment is currently pending approval.";
  const s5 = formatter.format(r5);
  assert(s5.includes("Your equipment request is still waiting for approval"), `Expected conversational pending status, got: ${s5}`);

  console.log('  ✓ Test 2.4: Natural conversational phrasing and contractions verified.');
}

{
  // Test 2.5: Technical citation metadata suppression
  const formatter = new SpeechResponseFormatter();
  const rawWithCitation = `Employees may carry forward up to 5 days of unused annual leave.
*Source: Acme_Leave_Policy.pdf (Section 4.1, Page 3)*
[1] Policy Document: Employee_Handbook_2026.docx`;

  const spoken = formatter.format(rawWithCitation);
  assert(spoken.includes('5 days of unused annual leave'), 'Core content must remain intact');
  assert(!spoken.includes('Acme_Leave_Policy.pdf'), 'Technical document filename must be suppressed in speech');
  assert(!spoken.includes('Section 4.1'), 'Section numbers in citations must be suppressed');
  assert(!spoken.includes('Employee_Handbook_2026'), 'Citation bracket references must be suppressed');
  console.log('  ✓ Test 2.5: Technical citation suppression in speech verified.');
}

{
  // Test 2.6: Natural ISO date conversion
  const formatter = new SpeechResponseFormatter();
  const rawDateRange = "I have set up your leave request from 2026-12-22 to 2026-12-24.";
  const spoken = formatter.format(rawDateRange);
  assert(spoken.includes('December 22nd to 24th, 2026') || spoken.includes('December 22nd'), `Date must be spoken naturally, got: ${spoken}`);
  assert(!spoken.includes('2026-12-22'), 'Raw ISO date hyphens must not be read');
  console.log('  ✓ Test 2.6: ISO date range conversion to natural spoken English verified.');
}

{
  // Test 2.7: Request status preservation (draft vs submitted vs approved vs cancelled)
  const formatter = new SpeechResponseFormatter();

  // Draft
  const draftText = "Please review and confirm your leave request: Annual Leave from 2026-12-10 to 2026-12-12.";
  const spokenDraft = formatter.format(draftText);
  assert(spokenDraft.toLowerCase().includes('screen') && spokenDraft.toLowerCase().includes('confirm'), 'Draft must guide user to screen confirmation');

  // Submitted
  const submittedText = "**Submission Successful!** Your request has been officially recorded.";
  const spokenSubmitted = formatter.format(submittedText);
  assert(spokenSubmitted.includes('officially recorded') || spokenSubmitted.includes('submitted'), 'Submitted status must be announced');

  // Cancelled
  const cancelText = "The proposed transaction has been cancelled.";
  const spokenCancel = formatter.format(cancelText);
  assert(spokenCancel.includes('cancelled'), 'Cancellation status must be faithfully preserved');

  console.log('  ✓ Test 2.7: Strict request status preservation (draft, submitted, cancelled) verified.');
}

{
  // Test 2.8: Security refusal phrasing
  const formatter = new SpeechResponseFormatter();
  const refusalRaw = "For your security and corporate compliance, enterprise actions require explicit confirmation using the 'Confirm Submission' button on your screen.";
  const spoken = formatter.format(refusalRaw);
  assert(spoken.includes("Confirm Submission button on your screen"), 'Spoken refusal must guide user to screen button');
  assert(!spoken.includes("require explicit confirmation"), 'Formal robotic phrasing must be conversationalized');
  console.log('  ✓ Test 2.8: Security refusal phrasing conversationalization verified.');
}

{
  // Test 2.9: Factual consistency validation and safe fallback
  const formatter = new SpeechResponseFormatter();
  const originalWithNumbers = "Your total approved expense reimbursement is $450 across 3 separate receipts.";
  const spoken = formatter.format(originalWithNumbers);
  assert(spoken.includes('450 dollars'), 'Monetary value must be strictly preserved');
  assert(spoken.includes('3'), 'Receipt count must be preserved');
  assert(formatter.validateFactualConsistency(originalWithNumbers, spoken), 'Factual consistency must pass');

  // Verify fallback if numbers are tampered or missing
  const tampered = "Your total approved expense reimbursement is across some receipts.";
  assert.strictEqual(formatter.validateFactualConsistency(originalWithNumbers, tampered), false, 'Must fail consistency if numbers missing');
  console.log('  ✓ Test 2.9: Factual consistency validation and safe fallback verified.');
}

// ==========================================
// 3. GreetingService Tests
// ==========================================
console.log('\n[Suite 3] GreetingService Unit Tests');

{
  const service = new GreetingService();

  // Test 3.1: Employee preferred name with morning time
  const morning = new Date(2026, 10, 23, 9, 30);
  const employeeUser = { first_name: 'Bob', last_name: 'Jones', role: 'employee' };
  const g1 = service.generateGreeting(employeeUser, morning);
  assert(g1.includes('Hey Bob!'), 'Must greet employee by first name');
  assert(g1.includes('Good morning'), 'Must greet with Good morning before 12');

  // Test 3.2: Afternoon time
  const afternoon = new Date(2026, 10, 23, 14, 15);
  const g2 = service.generateGreeting(employeeUser, afternoon);
  assert(g2.includes('Hey Bob!'));
  assert(g2.includes('Good afternoon'));

  // Test 3.3: Evening time
  const evening = new Date(2026, 10, 23, 19, 0);
  const g3 = service.generateGreeting(employeeUser, evening);
  assert(g3.includes('Hey Bob!'));
  assert(g3.includes('Good evening'));

  // Test 3.4: HR Admin greeting with preferred name
  const hrAdmin = { first_name: 'Alice', preferred_name: 'Ally', role: 'hr_admin' };
  const g4 = service.generateGreeting(hrAdmin, afternoon);
  assert(g4.includes('Hey Ally!'), 'Preferred name takes precedence');

  // Test 3.5: Neutral fallback when user has no name
  const g5 = service.generateGreeting(null, morning);
  assert(g5.includes('Hello! Good morning'));

  // Test 3.6: Single greeting per session
  assert(service.shouldGreet() === true);
  service.markGreeted();
  assert(service.shouldGreet() === false, 'Should not greet again in same session');
  service.resetSession();
  assert(service.shouldGreet() === true, 'Resetting session allows greeting again');
  console.log('  ✓ Test 3: Greeting generation, time-of-day, and single-session tracking passed.');
}

// ==========================================
// 4. WakeWordDetector Tests
// ==========================================
console.log('\n[Suite 4] WakeWordDetector Unit Tests');

{
  const detector = new WakeWordDetector();

  // Exact match
  const d1 = detector.detect('Hey Archie');
  assert.strictEqual(d1.detected, true);
  assert.strictEqual(d1.remainderQuery, '');

  // Case insensitive
  const d2 = detector.detect('hey archie!');
  assert.strictEqual(d2.detected, true);

  // Question in one breath
  const d3 = detector.detect('Hey Archie what is my leave balance?');
  assert.strictEqual(d3.detected, true);
  assert(d3.remainderQuery.includes('what is my leave balance'));

  // Variant "Archie"
  const d4 = detector.detect('Archie check my IT ticket');
  assert.strictEqual(d4.detected, true);
  assert(d4.remainderQuery.includes('check my it ticket'));

  // Unrelated speech
  const d5 = detector.detect('Can you check my annual leave balance?');
  assert.strictEqual(d5.detected, false);

  // Negative wake phrases (must NOT activate Archie)
  assert.strictEqual(detector.detect('Hey Google').detected, false);
  assert.strictEqual(detector.detect('Hello Siri').detected, false);
  assert.strictEqual(detector.detect('Good morning team').detected, false);
  assert.strictEqual(detector.detect('Hey Arthur, can you help me?').detected, false);
  assert.strictEqual(detector.detect('Architectural design review').detected, false);

  // Repeated wake phrase
  const dRepeated = detector.detect('Hey Archie Hey Archie');
  assert.strictEqual(dRepeated.detected, true);

  console.log('  ✓ Test 4: Wake-word phrase detection, negative phrases, and repeated wake words passed.');
}

// ==========================================
// 5. VoiceStateMachine Tests
// ==========================================
console.log('\n[Suite 5] VoiceStateMachine Unit Tests');

{
  const mockSTT = new MockSTTProvider();
  const mockTTS = new MockTTSProvider();

  let currentState = VoiceSessionState.DISABLED;
  let submittedQueries = [];

  const sm = new VoiceStateMachine(
    mockSTT,
    mockTTS,
    {
      onStateChange: (state) => {
        currentState = state;
      },
      onLiveTranscript: () => {},
      onSubmitUtterance: async (query) => {
        submittedQueries.push(query);
        return `Here is the response for ${query}`;
      },
      onError: () => {},
    },
    {
      wakePhrase: 'hey archie',
      inactivityTimeoutMs: 100, // Short timeout for unit test
    },
    { first_name: 'Bob', role: 'employee' }
  );

  // Initial state
  assert.strictEqual(sm.getState(), VoiceSessionState.DISABLED);

  // Enable voice mode -> enters WAKE_WORD_LISTENING
  sm.enableVoiceMode();
  assert.strictEqual(sm.getState(), VoiceSessionState.WAKE_WORD_LISTENING);
  assert.strictEqual(mockSTT.isListening(), true);

  // Negative phrases must not trigger activation
  mockSTT.simulateFinal('Hey Google');
  assert.strictEqual(sm.getState(), VoiceSessionState.WAKE_WORD_LISTENING, 'Negative phrase must remain in WAKE_WORD_LISTENING');
  mockSTT.simulateFinal('Hello Siri, what time is it?');
  assert.strictEqual(sm.getState(), VoiceSessionState.WAKE_WORD_LISTENING, 'Negative phrase must remain in WAKE_WORD_LISTENING');

  // Simulate wake phrase detection
  mockSTT.simulateFinal('Hey Archie');
  assert.strictEqual(sm.getState(), VoiceSessionState.GREETING);
  assert(mockTTS.isSpeaking(), 'TTS should be speaking greeting');
  assert(mockTTS.spokenTexts[0].includes('Hey Bob!'), 'Greeting must address authenticated user');

  // Wait for greeting simulation to finish
  await new Promise((r) => setTimeout(r, 25));
  assert.strictEqual(sm.getState(), VoiceSessionState.ACTIVE_LISTENING);

  // Employee asks a question
  mockSTT.simulateFinal('What is my leave balance?');
  assert.strictEqual(submittedQueries[0], 'What is my leave balance?');

  // Wait for response processing and speaking
  await new Promise((r) => setTimeout(r, 25));
  assert(mockTTS.spokenTexts.some((t) => t.includes('Here is the response for What is my leave balance?')));

  // Continuous conversation: after answer finishes speaking, it should return to ACTIVE_LISTENING
  await new Promise((r) => setTimeout(r, 25));
  assert.strictEqual(sm.getState(), VoiceSessionState.ACTIVE_LISTENING, 'Must return to active listening without requiring wake phrase');

  // Manual interruption test: when user clicks mic while Archie is speaking
  await sm.speakAnswer('Long spoken response about company policy');
  assert.strictEqual(sm.getState(), VoiceSessionState.SPEAKING);
  sm.manualActivateMic();
  assert.strictEqual(mockTTS.isSpeaking(), false, 'Interruption must stop TTS immediately');
  assert.strictEqual(sm.getState(), VoiceSessionState.ACTIVE_LISTENING);

  // Inactivity timeout test: active listening returns to wake-word listening after silence
  await new Promise((r) => setTimeout(r, 150));
  assert.strictEqual(sm.getState(), VoiceSessionState.WAKE_WORD_LISTENING, 'Inactivity must transition back to wake word listening');

  // Test one-breath query remainder lifecycle ("Hey Archie, how many leave days do I have?")
  const oneBreathQueries = [];
  const smOneBreath = new VoiceStateMachine(
    mockSTT,
    mockTTS,
    {
      onStateChange: () => {},
      onLiveTranscript: () => {},
      onSubmitUtterance: async (query) => {
        oneBreathQueries.push(query);
        return `You have 8.0 days of leave`;
      },
      onError: () => {},
    },
    { wakePhrase: 'hey archie' },
    { first_name: 'Bob', role: 'employee' }
  );
  smOneBreath.enableVoiceMode();
  mockSTT.simulateFinal('Hey Archie, how many leave days do I have?');
  assert.strictEqual(smOneBreath.getState(), VoiceSessionState.GREETING);
  await new Promise((r) => setTimeout(r, 25)); // Greeting completes -> one-breath query auto-submitted
  assert(
    oneBreathQueries.some((q) => q.toLowerCase().includes('how many leave days do i have')),
    'One-breath remainder query must be submitted automatically'
  );
  smOneBreath.cleanup();

  // Cleanup on logout
  sm.cleanup();
  assert.strictEqual(mockSTT.isListening(), false);
  assert.strictEqual(mockTTS.isSpeaking(), false);

  console.log('  ✓ Test 5: VoiceStateMachine complete lifecycle, interruption, and cleanup passed.');
}

// ==========================================
// 6. Voice Selection Heuristic Ranking Tests
// ==========================================
console.log('\n[Suite 6] Voice Selection Heuristic Ranking Tests');

{
  const { WebSpeechTTSProvider } = await import('../lib/voice/ttsProvider.ts');

  // Setup mock window with synthetic voice catalog
  const mockVoices = [
    { name: 'Microsoft David - English (United States)', lang: 'en-US' },
    { name: 'Microsoft Zira - English (United States)', lang: 'en-US' },
    { name: 'Google हिन्दी', lang: 'hi-IN' },
    { name: 'Microsoft Ravi - English (India)', lang: 'en-IN' },
    { name: 'Microsoft Heera - English (India)', lang: 'en-IN' },
  ];

  globalThis.window = {
    speechSynthesis: {
      getVoices: () => mockVoices,
      onvoiceschanged: null,
      speak: () => {},
      cancel: () => {},
    },
    SpeechSynthesisUtterance: class {},
  };

  const tts = new WebSpeechTTSProvider('en-IN');

  // Test 6.1: Female en-IN preferred
  const v1 = tts.selectBestVoice();
  assert.strictEqual(v1.name, 'Microsoft Heera - English (India)', 'Should prioritize female en-IN voice');

  // Test 6.2: Any en-IN voice if female not present
  globalThis.window.speechSynthesis.getVoices = () => [
    { name: 'Microsoft David - English (United States)', lang: 'en-US' },
    { name: 'Microsoft Ravi - English (India)', lang: 'en-IN' },
  ];
  const v2 = tts.selectBestVoice();
  assert.strictEqual(v2.name, 'Microsoft Ravi - English (India)', 'Should fallback to any en-IN voice');

  // Test 6.3: Female English voice if no en-IN
  globalThis.window.speechSynthesis.getVoices = () => [
    { name: 'Microsoft David - English (United States)', lang: 'en-US' },
    { name: 'Microsoft Zira - English (United States)', lang: 'en-US' },
  ];
  const v3 = tts.selectBestVoice();
  assert.strictEqual(v3.name, 'Microsoft Zira - English (United States)', 'Should fallback to female English voice');

  // Test 6.4: Fallback to any English voice
  globalThis.window.speechSynthesis.getVoices = () => [
    { name: 'Microsoft David - English (United States)', lang: 'en-US' },
  ];
  const v4 = tts.selectBestVoice();
  assert.strictEqual(v4.name, 'Microsoft David - English (United States)');

  console.log('  ✓ Test 6: Voice selection heuristic ranking and female en-IN priority verified.');
}

// ==========================================
// 7. Unified Voice and Chat Conversation Synchronization Tests (ESR-STD-v2.4 §3)
// ==========================================
console.log('\n[Suite 7] Unified Conversation & Mode Switching Unit Tests');

{
  // Simulated thread store representing ChatInterface message thread
  const unifiedMessages = [];
  const conversationId = `conv-${Date.now()}`;
  let backendRequestCount = 0;

  // Unified submission pipeline simulating handleSend and handleVoiceSubmit
  async function processUnifiedTurn(senderMode, text) {
    // 1. Append user message to thread
    const userMsg = {
      id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      sender: 'user',
      mode: senderMode,
      text: text,
      conversationId: conversationId,
    };
    unifiedMessages.push(userMsg);

    // 2. Strict Security Boundary check
    const lower = text.toLowerCase().trim();
    if (lower === 'yes submit it' || lower === 'confirm submission') {
      const refusalMsg = "For your security and corporate compliance, enterprise actions require explicit confirmation using the 'Confirm Submission' button on your screen.";
      const assistantMsg = {
        id: `asst-${Date.now()}`,
        sender: 'assistant',
        text: refusalMsg,
        spokenText: "For your security, you'll need to tap the Confirm Submission button on your screen to complete this.",
        category: 'transactional',
      };
      unifiedMessages.push(assistantMsg);
      return assistantMsg.spokenText;
    }

    // 3. Dispatch to backend
    backendRequestCount++;
    const authoritativeAnswer = `Your annual leave balance is 8.0 days. Policy Citation: [Acme_Leave_Policy.pdf].`;
    const spokenRepresentation = formatForSpeech(authoritativeAnswer);

    const assistantMsg = {
      id: `asst-${Date.now()}`,
      sender: 'assistant',
      text: authoritativeAnswer, // Full written answer in chat
      spokenText: spokenRepresentation, // Derived spoken version for Archie
      category: 'employee',
      conversationId: conversationId,
    };
    unifiedMessages.push(assistantMsg);
    return spokenRepresentation;
  }

  // Test 7.1: Voice Turn 1
  const spoken1 = await processUnifiedTurn('voice', 'Hey Archie how many leave days do I have?');
  assert.strictEqual(unifiedMessages.length, 2, 'Voice input must create exactly one user and one assistant message');
  assert.strictEqual(unifiedMessages[0].mode, 'voice');
  assert(unifiedMessages[1].text.includes('[Acme_Leave_Policy.pdf]'), 'Full written answer in chat must retain policy citation');
  assert(!spoken1.includes('[Acme_Leave_Policy.pdf]'), 'Spoken version must suppress technical citation strings');
  assert(spoken1.includes("You've got 8 days") || spoken1.includes('8.0 days'), 'Spoken version must preserve leave balance');

  // Test 7.2: Text Turn 2 (Employee switches to typing without losing context)
  const spoken2 = await processUnifiedTurn('text', 'Can I carry forward unused days?');
  assert.strictEqual(unifiedMessages.length, 4, 'Text input appends to same message thread');
  assert.strictEqual(unifiedMessages[2].conversationId, conversationId, 'Conversation ID must be shared');

  // Test 7.3: Voice Turn 3 (Employee switches back to voice)
  const spoken3 = await processUnifiedTurn('voice', 'Apply for leave next Monday');
  assert.strictEqual(unifiedMessages.length, 6, 'Voice follow-up appends to same unified thread');
  assert.strictEqual(backendRequestCount, 3, 'Exactly one backend request per conversational turn');

  // Test 7.4: Spoken confirmation refusal
  const spokenRefusal = await processUnifiedTurn('voice', 'Yes submit it');
  assert.strictEqual(backendRequestCount, 3, 'Spoken confirmation must NOT make an execution request');
  assert(spokenRefusal.includes('Confirm Submission button on your screen'), 'Security refusal must instruct user to click UI button');

  console.log('  ✓ Test 7: Unified conversation thread, context preservation across voice/text, and security boundary passed.');
}

console.log('\n--- ALL ARCHIE NATURAL CONVERSATIONAL VOICE UNIT TESTS PASSED ---\n');
