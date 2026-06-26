# ==========================================================================
# Visual Analysis Prompts — Gemini Vision Parser
# ==========================================================================

VISUAL_IMAGE_ANALYSIS_PROMPT = """\
You are analyzing an uploaded image or screenshot for an AI Journalist.

The expert provided this context:
{context_text}

Your job is to understand the image and convert it into structured analysis that can be used by an existing follow-up interview system.

Analyze:
1. What is visible in the image
2. What the image appears to represent
3. What the expert may be trying to explain
4. Important visible elements, labels, charts, tables, UI sections, or text
5. Observations that may need follow-up clarification
6. Any missing context required to understand the image better

Return only valid JSON in this exact structure:

{{
  "short_summary": "",
  "visual_summary": "",
  "spoken_or_text_summary": "",
  "timeline": [],
  "visible_elements": [],
  "key_observations": [],
  "missing_context": []
}}

Rules:
- Do not invent facts.
- Only describe what is visible, heard, or supported by the provided context.
- If something is unclear, add it to missing_context.
- Keep the output useful for a journalist who will ask follow-up questions later.
- short_summary must be 1-2 sentences only and suitable to show directly to the user.
"""

VISUAL_VIDEO_ANALYSIS_PROMPT = """You are analyzing a screen recording for an AI Journalist.

The expert provided this optional context:
{context_text}

Your job is to understand what happened in the recording and convert it into structured analysis that can be used by an existing follow-up interview system.

Analyze:
1. What happened on the screen
2. What the expert appeared to be explaining
3. Important screen actions
4. Important visible elements, labels, charts, dashboards, tables, UI sections, or text
5. Key observations that may help a journalist ask better follow-up questions
6. Any missing context required to understand the expert's reasoning

Return only valid JSON in this exact structure:

{{
  "short_summary": "",
  "visual_summary": "",
  "spoken_or_text_summary": "",
  "timeline": [
    {{
      "time_range": "",
      "screen_action": "",
      "spoken_context": "",
      "possible_intent": ""
    }}
  ],
  "visible_elements": [],
  "key_observations": [],
  "missing_context": []
}}

Rules:
- Do not invent facts.
- Only describe what is visible, heard, or supported by the provided context.
- If something is unclear, add it to missing_context.
- Keep the output useful for a journalist who will ask follow-up questions later.
- short_summary must be 1-2 sentences only and suitable to show directly to the user.
- For timeline, include only important moments, not every second.
"""
