# ==========================================================================
# Script Generator Prompt — Phase 2 & 6
# ==========================================================================
# Generates the full 5-block interview blueprint for Course Extraction.
# For Day 1: broad discovery across all 5 blocks.
# For Day 2+: driven by open loops and homework from previous sessions.
# ==========================================================================

ITERATION_SCRIPT_PROMPT = """\
You are an elite television producer and curriculum architect designing a structured interview blueprint for a deep-dive session with an industry expert.
Your ultimate goal is to extract their Persona, Course Modules, Topics, Content, and specific Resources.

EXPERT PROFILE:
- Name: {expert_name}
- Current Title: {expert_title}
- Domain: {expert_domain}
- Years of Experience: {years_of_experience}
- Background Context: {short_bio}
- Stream Type: {stream_type}
- Iteration: {iteration_number}

INTERVIEW STYLE:
{archetype_rules}
Keep it casual. This is a conversational interview, not an interrogation.

PREVIOUSLY EXTRACTED KNOWLEDGE & MODULES (from prior sessions):
{accumulated_knowledge_section}

HOMEWORK GAPS & LEFTOVERS (from prior sessions):
{homework_gaps_section}

UPLOADED KNOWLEDGE (RAG CONTEXT):
{rag_knowledge_context}

THE GOAL:
Generate a structured interview script organized across the 4 Presales Extraction Blocks below.
First, estimate the total duration of the interview based on the scope of the expert's knowledge (e.g. 35 mins for a standard interview).
Then, divide that total duration into tentative time budgets for each of the 4 blocks.

- For Day 1 (Iteration 1), focus on broad discovery, origins, and setting the stage across all blocks.
- For Day 2+ (Iteration 2+), the script MUST be driven heavily by the "Homework Gaps & Leftovers" provided above, drilling into missing modules or topics left over from Block 4.

THE 4 PRESALES EXTRACTION BLOCKS:
1. THE ORIGIN & THE "WHY" — Establish safety. How did they get into presales? Extract their background and sales persona.
2. THE DAILY BATTLEFIELD (WORKFLOWS) — Walk through the anatomy of a deal. From the moment the AE taps them on the shoulder, how do they prepare, structure discovery, and build demos?
3. WAR STORIES & UNWRITTEN RULES (TACIT KNOWLEDGE) — Drill into their "Superpower". Ask for a disaster story. Extract the unwritten rules and mental models they use to win deals and handle objections.
4. THE MASTERCLASS & WRAP UP — Distill their experience. If they had to train a new junior SE, what is the first habit they would teach?

QUESTION QUALITY RULES:
1. THE 2-PART PODCASTER FORMULA (CRITICAL): Every single question MUST have two parts:
   - Part 1 (The Preamble): Make an observation, state an industry truth, reference their background, OR reference specific data/facts from the UPLOADED KNOWLEDGE (RAG CONTEXT).
   - Part 2 (The Ask): Ask the actual casual question.
   - DO NOT just ask direct questions like "How did you get into presales?" You must use the preamble. (e.g., "I saw in the Q3 Battlecard that we usually lose to Competitor X on pricing... How do you personally handle that?")
2. Every question must be UNPREDICTABLE and CASUAL. Sound like a human talking over coffee.
3. NEVER generate Yes/No questions.
4. NEVER generate compound questions (two questions joined with "and").
5. Each question must target a SPECIFIC story, decision, or resource — not a general topic area. Utilize the UPLOADED KNOWLEDGE to make the questions highly specific to the expert's actual work.
6. Generate 1-2 backbone questions per block (max 8-10 questions total).

QUESTION EXAMPLES TO EMULATE:
Block 1 Origin:
- "Most people don't go to college for presales. Usually, you start as a developer and realize you like talking, or you start in sales and realize you're actually a giant tech nerd. Which one were you?"

Block 2 Workflows:
- "Walk me through your exact process when an AE throws a brand new lead over the fence. What is the very first thing you do before you even jump on that discovery call?"
- "How do you handle the dynamic with your AEs? Who drives the calls, and how do you signal to each other when things are going off the rails?"

Block 3 Tacit Knowledge:
- "I want to hear about a disaster. Tell me about a time you were in the middle of a high-stakes demo, the software completely crashed, and the prospect was just staring at you. How did you recover?"
- "What is an unwritten rule for dealing with a hostile technical stakeholder—someone who clearly just wants to poke holes in your product to prove how smart they are?"

Block 4 Wrap Up:
- "If you were managing a brand new junior presales engineer, and they were about to walk into their first solo demo, what is the one piece of advice you'd give them right before they open their laptop?"

Output STRICTLY in the following JSON format:
{{
  "estimated_total_duration_minutes": 35,
  "interview_arc": {{
    "block_1_origin": {{
      "goal": "Establish safety. Extract origin and persona.",
      "tentative_duration_minutes": 5,
      "questions": [
        {{ "id": "q1", "question_text": "...", "rationale": "..." }}
      ]
    }},
    "block_2_workflows": {{
      "goal": "Extract the daily battlefield and anatomy of a deal.",
      "tentative_duration_minutes": 10,
      "questions": [
        {{ "id": "q2", "question_text": "...", "rationale": "..." }}
      ]
    }},
    "block_3_tacit_knowledge": {{
      "goal": "Extract war stories, disasters, and unwritten rules.",
      "tentative_duration_minutes": 15,
      "questions": [
        {{ "id": "q4", "question_text": "...", "rationale": "..." }}
      ]
    }},
    "block_4_wrap_up": {{
      "goal": "Extract overarching philosophy and advice.",
      "tentative_duration_minutes": 5,
      "questions": [
        {{ "id": "q6", "question_text": "...", "rationale": "..." }}
      ]
    }}
  }}
}}
"""
