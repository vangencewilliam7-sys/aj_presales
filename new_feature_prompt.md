# New Feature Prompt

*(Paste your new feature request or prompt here)*
Build Feature 2 of AI Journalist Visual Input Parser: Screen Share + Explain.

Context:
Image/Screenshot Upload + Gemini Parse is already built. Now we need to add the screen share recording option.

Important:
Do not rebuild image upload.
Do not rebuild the follow-up system.
Do not rebuild tacit knowledge extraction or final content generation.
This task is only to add screen recording with microphone, upload the recorded video, send it through the existing visual input backend/Gemini flow, and then continue into the existing follow-up flow.

Feature name:
Screen Share + Explain

Goal:
Allow the expert to share their screen, speak while explaining, record the screen + microphone audio, and send the recorded video to the backend for Gemini parsing. After Gemini parses the video, the app should show only a short summary and the first follow-up question from the existing follow-up system.

User flow:
1. User selects "Screen Share + Explain".
2. App shows a short instruction:
   "Share your screen and explain your process. We will record your screen and voice, then AI Journalist will understand it and continue the interview."
3. User clicks "Start Recording".
4. Browser asks the user to choose screen/window/tab.
5. Browser asks for microphone permission.
6. App records screen + mic audio.
7. App shows recording timer.
8. User clicks "Stop Recording".
9. App creates a recorded video file, preferably WebM.
10. User can preview the recording.
11. User clicks "Analyze Recording".
12. Frontend sends the recorded video to the existing visual input analyze endpoint.
13. Backend stores the recording in Supabase Storage.
14. Backend stores metadata in journalist_visual_inputs.
15. Backend sends the recording to Gemini video analysis.
16. Backend stores the full Gemini analysis in journalist_visual_analysis.
17. Backend passes the analysis to the existing follow-up flow.
18. Frontend shows only:
   - short 1-2 sentence summary
   - first follow-up question

Frontend requirements:
1. Add a new option:
   "Screen Share + Explain"

2. When selected, show:
   - Start Recording button
   - Short instruction text
   - Permission guidance
   - Recording timer
   - Stop Recording button
   - Recording preview after stop
   - Analyze Recording button

3. Use browser APIs:
   - navigator.mediaDevices.getDisplayMedia() for screen capture
   - navigator.mediaDevices.getUserMedia() for microphone capture
   - MediaRecorder for recording

4. Recording behavior:
   - Capture screen video.
   - Capture microphone audio.
   - Combine screen stream and microphone audio into one MediaStream.
   - Use MediaRecorder to record the combined stream.
   - Store recorded chunks in memory while recording.
   - On stop, create a Blob file.
   - File type should be video/webm if supported.
   - File name can be:
     screen-explain-{timestamp}.webm

5. UI states:
   Before recording:
   - Show Start Recording button.

   During recording:
   - Show "Recording..."
   - Show timer like 00:01, 00:02, etc.
   - Show Stop Recording button.

   After recording:
   - Show video preview.
   - Show Analyze Recording button.
   - Allow user to discard and record again.

6. On clicking Analyze Recording:
   Send multipart/form-data request to:
   POST /api/journalist/visual-input/analyze

Request payload:
- session_id
- user_id
- input_type = screen_recording
- context_text, optional
- file = recorded WebM video

7. Loading state:
   Show:
   "Understanding your recording..."

8. Final user-facing output:
   Do not show detailed Gemini analysis.
   Show only:
   - short_summary
   - first_follow_up_question

Example:
"Got it. You walked through a dashboard and explained how you review lead quality using source and conversion signals.

Why do you check lead source before looking at total lead count?"

Backend requirements:
1. Update existing endpoint:
   POST /api/journalist/visual-input/analyze

2. It already supports input_type=image.
   Now add support for:
   input_type=screen_recording

3. For screen_recording:
   Validate:
   - file exists
   - input_type is screen_recording
   - file type is video/webm or video/mp4
   - file size is within allowed limit
   - session_id is present

4. Recommended MVP file size limit:
   100MB

5. Upload recording to Supabase Storage bucket:
   journalist-visual-inputs

Storage path format:
   {user_id}/{session_id}/{timestamp}_screen_recording.webm

6. Insert file metadata into:
   journalist_visual_inputs

Fields:
- session_id
- user_id
- input_type = screen_recording
- file_name
- file_type
- file_size
- storage_path
- context_text
- status = uploaded

7. Send the video file to Gemini for video analysis.

Gemini video prompt:
"You are analyzing a screen recording for an AI Journalist.

The expert provided this optional context:
{{context_text}}

Your job is to understand what happened in the recording and convert it into structured analysis that can be used by an existing follow-up interview system.

Analyze:
1. What happened on the screen
2. What the expert appeared to be explaining
3. Important screen actions
4. Important visible elements, labels, charts, dashboards, tables, UI sections, or text
5. Key observations that may help a journalist ask better follow-up questions
6. Any missing context required to understand the expert's reasoning

Return only valid JSON in this exact structure:

{
  "short_summary": "",
  "visual_summary": "",
  "spoken_or_text_summary": "",
  "timeline": [
    {
      "time_range": "",
      "screen_action": "",
      "spoken_context": "",
      "possible_intent": ""
    }
  ],
  "visible_elements": [],
  "key_observations": [],
  "missing_context": []
}

Rules:
- Do not invent facts.
- Only describe what is visible, heard, or supported by the provided context.
- If something is unclear, add it to missing_context.
- Keep the output useful for a journalist who will ask follow-up questions later.
- short_summary must be 1-2 sentences only and suitable to show directly to the user.
- For timeline, include only important moments, not every second."

8. Save full Gemini analysis into:
   journalist_visual_analysis

Fields:
- session_id
- visual_input_id
- input_type = screen_recording
- visual_summary
- spoken_or_text_summary
- timeline_json
- visible_elements_json
- key_observations_json
- missing_context_json
- raw_gemini_response_json

9. Update journalist_visual_inputs.status to:
   parsed

10. Pass Gemini analysis to the existing follow-up flow.

The follow-up flow should receive:
{
  "session_id": "...",
  "source_type": "visual_input",
  "input_type": "screen_recording",
  "visual_input_id": "...",
  "analysis_id": "...",
  "analysis": {
    "short_summary": "",
    "visual_summary": "",
    "spoken_or_text_summary": "",
    "timeline": [],
    "visible_elements": [],
    "key_observations": [],
    "missing_context": []
  }
}

11. Existing follow-up flow should generate the first follow-up question.

12. Backend response to frontend should be:
{
  "success": true,
  "session_id": "...",
  "visual_input_id": "...",
  "analysis_id": "...",
  "short_summary": "...",
  "first_follow_up_question": "..."
}

Frontend should display:
short_summary + first_follow_up_question

Supabase:
Use existing bucket:
journalist-visual-inputs

Use existing tables:
journalist_visual_inputs
journalist_visual_analysis

No new tables are required.

Security:
- Do not expose GEMINI_API_KEY on frontend.
- Do not expose SUPABASE_SERVICE_ROLE_KEY on frontend.
- Gemini and Supabase service role calls must happen only from backend.

Error handling:
If screen permission is denied:
Show:
"Screen sharing permission was denied. Please allow screen sharing to record your explanation."

If microphone permission is denied:
Show:
"Microphone permission was denied. Please allow microphone access so your explanation can be captured."

If recording fails:
Show:
"Recording could not be started. Please try again."

If upload fails:
Show:
"Recording upload failed. Please try again."

If Gemini fails:
Update journalist_visual_inputs.status to failed and return:
{
  "success": false,
  "message": "Recording analysis failed. Please try again.",
  "error_code": "GEMINI_ANALYSIS_FAILED"
}

Do not build in this step:
- uploaded video option
- live AI watching screen in real time
- AI interruption during recording
- multi-user meeting capture
- new follow-up engine
- tacit knowledge extraction
- final content generation
- vector database

Success criteria:
1. User can choose Screen Share + Explain.
2. User can start screen recording with microphone.
3. User can stop recording.
4. User can preview the recorded video.
5. User can send the recording for analysis.
6. Recording is stored in Supabase Storage.
7. Metadata is stored in journalist_visual_inputs.
8. Gemini parses the recording.
9. Full analysis is stored in journalist_visual_analysis.
10. Existing follow-up flow receives the parsed analysis.
11. User sees only a short summary and first follow-up question.