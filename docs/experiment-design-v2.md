# Experiment Design v2: Competing Diagnoses

## Status: Active design (April 2026)
This document describes the current 3-arm design: C1 (single) / C2 (integrated) / C3 (competing). The system architecture (FastAPI + PostgreSQL + invite codes + conversation memory) remains the same; what changes is the treatment structure and AI prompt logic.

---

## Core Research Question

When AI generates multiple causal diagnoses of the same entrepreneurial problem, does the **presentation structure** (integrated vs. preserved disagreement) affect the quality of the entrepreneur's own problem formulation?

## Theoretical Anchors

- **Baer et al. (2013)**: Problem formulation = translating symptoms into alternative causal formulations. Comprehensiveness = how many nonredundant, relevant causes the decision-maker considers.
- **Kaplan (2008)**: Frame incongruence disrupts automatic categorization (Dutton, 1993), forcing deliberate formulation.
- **Wu et al. (2025)**: A single AI output at the formulation stage produces anchoring — decision-makers treat the AI's frame as settled and skip their own diagnosis.

## Mechanism

Preserved disagreement forces entrepreneurs to draw on their own first-hand knowledge to evaluate which diagnosis best fits their evidence. Resolved disagreement allows entrepreneurs to adopt the AI's conclusion directly, bypassing formulation. Same content, different structure, different cognitive outcome.

---

## Example (Grace, chapati seller in Palabek)

Three agents analyze the same intake information and produce competing causal diagnoses:

- **One reading of your situation**: "Based on what you told us, we believe your core problem is customer awareness — people in the settlement don't know your product exists. If this is correct, you should see that people who do try your chapati tend to come back, but new customers are rare. Your priority should be visibility, not product changes."
- **A different reading**: "We see a different pattern. Your core problem is perceived value relative to price — customers know about you but choose cheaper alternatives. If this is correct, you should see that customers visit but don't buy, or buy once but switch. Your priority should be either reducing costs or increasing perceived quality."
- **A third possibility**: "We disagree with both readings. Your core problem is inconsistent quality — you sometimes deliver a good product but can't do it reliably. If this is correct, you should see that some days sell well and others don't, and repeat customers are unpredictable. Your priority should be standardizing your production process."

### Prompt File Structure

```
backend/app/prompts/
├── intake.md                      # Shared across all arms
├── shared/
│   ├── conversation_rules.md
│   └── knowledge/                 # Industry knowledge files
├── agents/
│   ├── agent_a.md                 # First analytical lens
│   ├── agent_b.md                 # Second analytical lens
│   ├── agent_c.md                 # Third analytical lens
│   └── integrator.md              # For Condition 2: synthesizes 3 diagnoses into 1
```

> **Note on ideation/creative reframing version**: An alternative version where agents generate competing *opportunity frames* ("what could your business become?") instead of competing *causal diagnoses* ("what is wrong?") was considered but removed from this design doc. If needed for advisor discussions, see `docs/archive/ideation-version-notes.md`. The ideation version is not part of the current experiment because its theoretical home (Perry-Smith, Rindova & Martins, Doshi & Hauser) does not overlap with the paper's literature (Baer, Kaplan, Nickerson), and its DV (creative novelty) is fundamentally different from formulation comprehensiveness.

---

## Three Arms

### Conversation Flow

All arms share a common **intake phase**, then diverge:

```
┌─────────────────────────────────────────────┐
│           INTAKE PHASE (all arms)            │
│  AI asks 5-6 structured questions:           │
│  1. What is your business?                   │
│  2. What problem are you facing?             │
│  3. What have you tried so far?              │
│  4. Who are your customers?                  │
│  5. Who are your competitors?                │
│  6. Where does your money come from?         │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Condition 1  Condition 2  Condition 3
        │          │          │
        ▼          ▼          ▼
   [AI output shown, varies by condition]
        │          │          │
        ▼          ▼          ▼
   SAME NEUTRAL RESPONSE PROMPT (all arms)
```

### Condition 1: Single Diagnosis

- **Backend**: 1 standard AI call generates 1 diagnosis based on intake information. This is an unconstrained, normal AI response — approximating how entrepreneurs currently use ChatGPT/Claude (ask one question, get one answer). No agent roles, no analytical lens constraints.
- **Entrepreneur sees**: 1 diagnosis + 1 recommended next step
- **Why unconstrained, not random selection from 3 agents**: Condition 1 is the ecological baseline — it represents normal AI use. The primary hypothesis (H1) is C2 vs. C3, which share identical backend content. C1 serves as a benchmark for H2 (does multi-perspective AI improve formulation even when integrated?). Using a constrained agent output would not represent how entrepreneurs actually use AI.

### Condition 2: Hidden Disagreement (Integrated Recommendation)

- **Backend**: 3 AI calls (3 different agent roles), each generates 1 diagnosis. A 4th AI call integrates them into 1 coherent recommendation.
- **Entrepreneur sees**: "We analyzed your situation from three angles. The key tension is between X and Y. On balance, we recommend Z because [reasons]."
- **Critical**: The entrepreneur sees the same core tensions as Condition 3 — but already resolved by the AI.

### Condition 3: Exposed Disagreement (Competing Diagnoses)

- **Backend**: Same 3 AI calls as Condition 2. Same agents, same knowledge, same intake. No integration step.
- **Entrepreneur sees**: 3 separate diagnoses, presented as "One reading of your situation..." / "A different reading..." / "A third possibility..."
- **Critical**: Same diagnostic content as Condition 2. Only difference is whether disagreement is resolved or preserved.

### Condition 3 Data Collection Step

After seeing the three diagnoses but **before** the neutral response prompt, Condition 3 entrepreneurs answer one selection question (for data collection, not as a treatment component):

> "Which of the three readings is closest to how you see your situation?"

This is logged but does not affect what happens next. All conditions then proceed to the same response prompt.

### Neutral Response Prompt (identical across all conditions)

After seeing their condition-specific AI output, **all entrepreneurs answer the same prompt**:

> "Based on what you just read, what do you think is the most important problem facing your business right now? What would you do next, and why?"

This is the primary DV elicitation. By using the same prompt across all conditions:
- Any difference in formulation quality must come from what they **saw**, not from the prompt
- No confound from differential cognitive demand of the response task
- Clean measurement: same question, same format, different upstream exposure

### Design Table

|                        | Condition 1          | Condition 2              | Condition 3              |
|------------------------|----------------------|--------------------------|--------------------------|
| Backend AI calls       | 1 (unconstrained)    | 3 + 1 integrator         | 3                        |
| Diagnostic content     | Normal single AI     | Broad (3 perspectives)   | Broad (3 perspectives)   |
| Disagreement visible?  | N/A                  | No (resolved)            | Yes (preserved)          |
| Data collection step   | —                    | —                        | "Which reading is closest?" |
| Response prompt        | **Identical neutral prompt** | **Identical neutral prompt** | **Identical neutral prompt** |
| Key comparison         | Ecological baseline  | vs. C1: does multi-perspective AI help? | vs. C2: does *seeing* disagreement help beyond *broader content*? |

---

## AI Agent Output Structure

Each agent's diagnosis MUST contain three parts:

**1. Cause** — A causal interpretation, not a symptom description, not an action tip.
- YES: "We believe your core problem is X because Y"
- NO: "Your sales are declining" (symptom — describes what's wrong, not why)
- NO: "You should lower your prices" (action tip — skips diagnosis entirely)

**2. Diagnostic Prediction** — A testable prediction that lets the entrepreneur evaluate against their own evidence.
- "If this diagnosis is correct, you should see [observable pattern]"
- This connects to Camuffo et al.'s "scientific approach" — turning diagnoses into testable hypotheses.
- This is what forces genuine evaluation: the entrepreneur checks the prediction against their own first-hand knowledge, not just their gut feeling.

**3. Implied Next Step** — Different diagnoses point to different action priorities, making "try all three" infeasible.
- "Your priority should be Z" — where Z differs across the three agents.
- The diagnoses do NOT need to be logically mutually exclusive, but they must be **action-incompatible**: the entrepreneur can only pursue one direction first.

### Agent Labels

Do NOT use expertise-domain labels like "Demand Analyst" / "Value Critic" / "Operations Analyst". These imply agents are discussing different topics rather than offering competing interpretations of the same problem.

Instead, use framing that explicitly signals disagreement:
- **"One reading of your situation:"** (Agent A)
- **"A different reading:"** (Agent B)
- **"A third possibility:"** (Agent C)

For Condition 2 (integrated), the integrator output uses: "We analyzed your situation from three angles..."

### Language Principles
- Use the entrepreneur's own words from intake (reduces cognitive load, increases relevance)
- Each agent output is 2-3 sentences max per part (~6-9 sentences total per agent)
- Simple language — no academic jargon, no business school frameworks
- Diagnoses are grounded in specific details the entrepreneur provided during intake
- Each agent explicitly references what the other agents got wrong: "We disagree with both readings because..."

---

## Changes Required to MentorLab System

### 1. Add Intake Phase
- New conversation state: `intake` (before arm-specific behavior kicks in)
- Intake AI uses a shared prompt (`prompts/intake.md`) with 5-6 structured questions
- Intake questions are the same across all arms
- Intake responses are stored and passed as context to the diagnosis generation step
- Intake ends when all questions are answered; system then triggers diagnosis generation

### 2. Add Multi-Agent Diagnosis Generation
- New service: `diagnosis_service.py` (or extend `claude_service.py`)
- **Condition 1**: 1 standard AI call (unconstrained, no agent role). Approximates normal AI use.
- **Conditions 2 & 3**: 3 parallel AI calls, each with a different agent role prompt + intake context. All 3 raw diagnoses stored in DB.
- **Condition 2 only**: 1 additional AI call with `integrator.md` prompt + the 3 diagnoses as input.
- **Condition 3 only**: All 3 diagnoses presented directly. No integration step.

### 3. Arm Prompts
- Current prompt files: `c1_single.md`, `c2_integrated.md`, `c3_competing.md`. Additional agent prompts:
  - `prompts/intake.md` (shared)
  - `prompts/agents/agent_a.md`, `agent_b.md`, `agent_c.md` (3 analytical lenses)
  - `prompts/agents/integrator.md` (for Condition 2)
- Arm assignment controls what the entrepreneur *sees*, not what the backend *generates*

### 4. Frontend Changes
- **Condition 3**: Display 3 diagnosis cards with framing labels ("One reading..." / "A different reading..." / "A third possibility..."). Below cards: selection form ("Which reading is closest?" — select one, logged as data).
- **All conditions**: After AI output, display the same neutral response prompt: "Based on what you just read, what do you think is the most important problem facing your business right now? What would you do next, and why?" + free text input.
- **Conditions 1 & 2**: Standard chat interface showing single AI output, then neutral prompt.

### 5. Database Changes
- New table or fields to store:
  - `diagnosis_raw` (JSON: for C1, the single AI output; for C2/C3, array of all 3 agent outputs)
  - `diagnosis_integrated` (the integrated output, for Condition 2 only)
  - `diagnosis_shown` (what the entrepreneur actually saw — text)
  - `selection_choice` (which reading selected as "closest", for Condition 3 only; integer 0-2)
  - `response_text` (entrepreneur's free-text response to the neutral prompt — ALL conditions)

### 6. Configuration
- Arm assignment still via invite codes (unchanged)
- Invite codes map to: `c1` / `c2` / `c3` (database arm values)

---

## Outcome Measures

### Primary DV: Problem Formulation Quality
Measured from the entrepreneur's free-text response to the neutral prompt. Blinded expert coders rate along two dimensions:

**Quantity-based**: Number of nonredundant, relevant causes identified (following Park & Baer 2022)

**Quality-based** (critical — prevents "more words = higher score" confound):
- Diagnosis clarity: does the entrepreneur identify a specific underlying cause rather than restating symptoms?
- Tradeoff articulation: does the entrepreneur acknowledge competing interpretations?
- Diagnosis-action coherence: does the proposed next step address the identified cause rather than sidestep it?
- Quality of the most important tension identified (not just number of tensions)

If C3 wins on quantity but not quality, the mechanism story is weak. Both must improve.

### Process Measures (required, not optional)
Collected immediately after the response prompt:
- **Cognitive load**: NASA-TLX raw variant
- **Perceived confusion**: "How clear was the advice you received?" (Likert)
- **Trust in AI advice**: "To what extent did you trust the advice?" (Likert)
- **Confidence in own diagnosis**: "How confident are you in your assessment of the problem?" (Likert)
- **Psychological ownership**: "To what extent does this plan feel like *your* plan?" (Likert)
- **Time on task**: reading time + writing time (logged automatically)

These distinguish "exposed disagreement improved formulation" from "exposed disagreement just created friction." If C3 shows higher formulation quality but also higher overload and lower ownership, the practical implications are different from a clean improvement.

### Secondary DVs
- Whether the entrepreneur revised their original strategic plan (binary)
- Whether the revision addresses the diagnosed cause vs. sidesteps it
- Whether the entrepreneur initiated new validation activities post-treatment

### Manipulation Checks
1. **Disagreement visibility**: "To what extent did you receive competing interpretations?" (Likert) + objective coding of whether explicit disagreement was present in AI output
2. **Breadth equivalence** (pre-field pilot): Independent raters verify C2 and C3 contain the same set of underlying diagnoses
3. **Comprehension**: Brief factual questions about what the AI output said

### Pre-Specified Heterogeneity
- **Baseline problem-formulation ability** (expert-coded quality of pre-treatment intake responses): Does exposed disagreement help more for entrepreneurs who already have some diagnostic capacity, or does it help most for those with weaker baselines?
- **Metacognition** (self-report): High-metacognition entrepreneurs may do well in all conditions; low-metacognition entrepreneurs may benefit most from C3's externally supplied alternatives (following Sun et al. 2025)

---

## Standardized Deliverable (all conditions)

To prevent ownership/agency confounds, all entrepreneurs across all conditions submit the same deliverable:
- Final problem diagnosis (free text)
- Proposed next step (free text)
- Why this is the right next step (free text)

All entrepreneurs are told: "You are responsible for this decision. The AI provided input, but the final plan is yours."

Submissions are stripped of arm-specific artifacts before expert coding. Neutral framing throughout: "different AI analysis workflows."

---

## Pilot Questions

These are the unknowns that the pilot (30-50 entrepreneurs) should answer before full launch:

1. **Engagement vs. freeze**: Do entrepreneurs engage with 3 competing diagnoses ("yes, the first one is closest") or freeze ("I don't know")?
2. **Diagnosis quality**: Are AI diagnoses grounded enough after intake? Or still fabricating?
3. **Diagnosis length**: Is 2-3 sentences per part enough? Too much? Too little?
4. **Number of agents**: Would 2 competing diagnoses work better than 3?
5. **Intake depth**: Are 5-6 questions enough context for meaningful diagnoses?
6. **Neutral prompt sensitivity**: Does the neutral prompt ("what do you think is the most important problem...") elicit meaningfully different responses across conditions, or do all conditions produce similar outputs?
7. **Diagnostic predictions**: Do entrepreneurs actually reference the "if this is correct, you should see..." patterns in their responses?

---

## Demo Plan for Kathy Meeting

Bring a realistic Uganda entrepreneur case (built from intake responses), show three screens:

1. **Condition 1**: "Here's what the entrepreneur sees — normal AI advice, one diagnosis"
2. **Condition 2**: "Here's the same entrepreneur with integrated multi-agent advice — same response prompt"
3. **Condition 3**: "Here's the same entrepreneur with exposed disagreement — same response prompt"

The key point for Kathy: all three conditions answer the same neutral question afterward. Any difference in formulation quality comes purely from what they saw upstream.

One-sentence question:
> "Does preserved disagreement activate formulation, or does it just create overload? And is Baer/Kaplan the right theoretical home?"
