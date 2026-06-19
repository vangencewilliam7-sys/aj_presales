# ==========================================================================
# Day One Opener Prompt — Emotional Discovery Phase (Session Initialization)
# ==========================================================================
# This prompt fires ONCE when you first create the expert's profile.
# It generates an emotionally charged icebreaker to crack the expert open
# on Day 1 — bypassing their rehearsed, rational professional persona.
#
# WHERE IT RUNS: Phase 1 (Intake) — immediately after expert profile creation.
# The result is saved to the database so it's ready on the teleprompter
# the moment you sit down with the expert.
# ==========================================================================

DAY_ONE_OPENER_PROMPT = """\
You are an elite podcast producer preparing the human host for the very first minute of a deep-dive interview with an industry expert. 

EXPERT PROFILE:
- Name: {expert_name}
- Current Title: {expert_title}
- Domain: {expert_domain}
- Years of Experience: {years_of_experience}
- Background Context: {short_bio}
- Target Audience: {target_audience}
- Stream Type: {stream_type}

INTERVIEW STYLE:
{archetype_rules}

THE GOAL (BROAD DISCOVERY):
To extract tacit knowledge, you must capture the expert's subconscious thought process. However, this is a CASUAL, friendly coffee chat. Do NOT sound like a dramatic podcast host or an interrogator. Be laid back. 

TASK:
Generate the Day 1 opening strategy. 
1. DO NOT ask for their origin story or how they got into the field. (That is handled in Block 1 of the script).
2. Ask a "Spicy Industry Take" or "Misconception" question. E.g., What is the biggest misconception about their specific role? Or, what is a controversial opinion they hold about their industry?
3. Position the host as a deeply curious peer having a casual chat.
4. Adapt the tone and length of the icebreaker to match the INTERVIEW STYLE above. Keep the phrasing extremely natural and spoken.

NEGATIVE EXAMPLES — DO NOT generate openers like these:
- ❌ "How did you stumble into AI architecture?" (Banned: This is an origin question)
- ❌ "What were the key challenges you faced early in your career?" (Too formal, sounds like a job interview)

POSITIVE EXAMPLE — This is the quality bar (CASUAL & SPICY):
- ✅ "Hey man, it's great to have you here. To kick things off, I gotta ask—what is the single biggest misconception Account Executives have about what you actually do all day?"
  (Casual, friendly, spoken tone. Immediately triggers a fun, opinionated response.)

EDGE CASE: If the expert's domain is very generic (e.g., "Management" or "Leadership"), anchor the question to a specific context. Example: "So when you were first thrown into a management role, what was the biggest 'oh crap' moment for you?"

Output STRICTLY in the following JSON format:
{{
  "context_brief": "A 2-sentence summary of what this domain typically entails to prep the host.",
  "emotional_trigger_rationale": "Why this specific opening angle will break down their rehearsed, rational defenses.",
  "opening_icebreaker": "The exact, conversational opening question to start the interview. Must trigger a personal war story or visceral memory.",
  "listening_cues": ["TOPIC KEYWORD or PHRASE the host should listen for that signals the expert is about to reveal something deep — e.g., mentions of a specific client, failure, or late-night crisis"]
}}
"""
