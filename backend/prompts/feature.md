Build Feature 3 of AI Journalist Visual Input Parser: Uploaded Video + Gemini Parse.

Context:
The following features are already implemented:
1. Image/Screenshot Upload + Gemini Parse
2. Screen Record + Explain

Now we need to add the third input type:
Uploaded Video / Screen Recording File

Important:
Do not rebuild image upload.
Do not rebuild screen recording.
Do not rebuild the follow-up system.
Do not rebuild tacit knowledge extraction or final content generation.

This task is only to allow the expert to upload an existing video file, send it to the existing visual input backend/Gemini flow, store the result, and continue into the existing follow-up interview flow.

Feature name:
Upload Video + AI Understanding

Goal:
Allow the expert to upload an existing screen recording or walkthrough video, optionally add context, and send the video to Gemini for parsing. After Gemini analyzes the video, the app should show only a short conversational summary and the first follow-up question from the existing follow-up flow.

User flow:
1. User selects "Upload Video / Screen Recording".
2. User uploads an existing video file.
3. User optionally adds a short explanation/context.
4. User clicks "Analyze Video".
5. Frontend sends the video file to the backend.
6. Backend stores the video in Supabase Storage.
7. Backend stores metadata in journalist_visual_inputs.
8. Backend sends the video to Gemini for video analysis.
9. Gemini returns structured analysis.
10. Backend stores the full Gemini analysis in journalist_visual_analysis.
11. Backend passes the analysis to the existing follow-up flow.
12. Frontend shows only:
   - short 1-2 sentence summary
   - first follow-up question from the existing follow-up flow

Do not show a detailed Gemini analysis report to the user.

Frontend requirements:
1. Add a new option:
   "Upload Video / Screen Recording"

2. Accepted file types:
   - MP4
   - MOV
   - WEBM

3. Do not accept:
   - images
   - PDFs
   - DOCX
   - XLSX
   - audio-only files

4. UI components:
   - Video upload area
   - File name and file size display
   - Video preview after upload
   - Optional context text box
   - Analyze Video button
   - Loading state
   - Error state
   - Option to remove selected video and upload another

5. Context text box placeholder:
   "Briefly explain what this video is about or what you want the AI Journalist to understand."

6. Analyze button text:
   "Analyze Video"

7. Loading message:
   "Understanding your video..."

8. After response, display only a conversational response:
   Example:
   "Got it. This video seems to show you walking through a campaign dashboard and explaining how you evaluate lead quality using source and conversion signals.

   Why do you check lead source before looking at total lead count?"

9. Do not display separate UI sections like:
   - Visual Summary
   - Spoken Summary
   - Timeline
   - Visible Elements
   - Key Observations
   - Missing Context

These details should be stored internally only.

Frontend API call:
Send multipart/form-data request to existing backend endpoint:

POST /api/journalist/visual-input/analyze

Request payload:
- session_id
- user_id
- input_type = video
- context_text
- file = uploaded video file

Backend requirements:
1. Update existing endpoint:
   POST /api/journalist/visual-input/analyze

2. It already supports:
   - input_type = image
   - input_type = screen_recording

3. Add support for:
   - input_type = video

4. Validation rules:
   - file must exist
   - session_id must exist
   - input_type must be video
   - file type must be video/mp4, video/quicktime, or video/webm
   - file extension must be .mp4, .mov, or .webm
   - file size must be within allowed limit

5. Recommended MVP file size limit:
   100MB

6. If file validation fails, return:
{
  "success": false,
  "message": "Only MP4, MOV, or WEBM videos under 100MB are supported."
}

7. Upload video to Supabase Storage bucket:
   journalist-visual-inputs

Storage path format:
   {user_id}/{session_id}/{timestamp}_uploaded_video_{file_name}

Example:
   user_123/session_456/1720000000_uploaded_video_dashboard_walkthrough.mp4

8. Insert file metadata into:
   journalist_visual_inputs

Fields:
- session_id
- user_id
- input_type = video
- file_name
- file_type
- file_size
- storage_path
- context_text
- status = uploaded

9. Send the uploaded video file to Gemini for video analysis.

Gemini video prompt:
"You are analyzing an uploaded video or screen recording for an AI Journalist.

The expert provided this optional context:
{{context_text}}

Your job is to understand what happens in the video and convert it into structured analysis that can be used by an existing follow-up interview system.

Analyze:
1. What happens on the screen or in the video
2. What the expert appears to be explaining
3. Important actions, moments, or transitions
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
- For timeline, include only important moments, not every second.
- If there is no clear audio, mention that spoken context could not be fully detected.
- If the video is mainly a screen recording, focus on screen actions and the likely workflow being explained."

10. Save full Gemini analysis into:
   journalist_visual_analysis

Fields:
- session_id
- visual_input_id
- input_type = video
- visual_summary
- spoken_or_text_summary
- timeline_json
- visible_elements_json
- key_observations_json
- missing_context_json
- raw_gemini_response_json

11. Update journalist_visual_inputs.status to:
   parsed

12. Pass Gemini analysis to the existing follow-up flow.

The follow-up flow should receive:
{
  "session_id": "...",
  "source_type": "visual_input",
  "input_type": "video",
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

13. Existing follow-up flow should generate the first follow-up question using this analysis.

14. Backend should return this response to frontend:
{
  "success": true,
  "session_id": "...",
  "visual_input_id": "...",
  "analysis_id": "...",
  "short_summary": "...",
  "first_follow_up_question": "..."
}

Frontend should display only:
short_summary + first_follow_up_question

Example final user-facing output:
"Got it. This video seems to show you walking through a campaign dashboard and explaining how you evaluate lead quality using source and conversion signals.

Why do you check lead source before looking at total lead count?"

Supabase requirements:
Use existing bucket:
journalist-visual-inputs

Use existing table:
journalist_visual_inputs

Use existing table:
journalist_visual_analysis

No new tables are required.

Expected status flow:
1. When video is uploaded:
   journalist_visual_inputs.status = uploaded

2. When video is sent to Gemini:
   journalist_visual_inputs.status = sent_to_gemini

3. When Gemini parsing is successful:
   journalist_visual_inputs.status = parsed

4. If parsing fails:
   journalist_visual_inputs.status = failed

Environment variables:
Use existing backend environment variables:
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- GEMINI_API_KEY

Security:
- Do not expose GEMINI_API_KEY on frontend.
- Do not expose SUPABASE_SERVICE_ROLE_KEY on frontend.
- Gemini and Supabase service role calls must happen only from backend.

Error handling:
If video file is missing, return:
{
  "success": false,
  "message": "Please upload a video before analysis."
}

If video type is unsupported, return:
{
  "success": false,
  "message": "Only MP4, MOV, or WEBM videos are supported."
}

If file is too large, return:
{
  "success": false,
  "message": "Video file is too large. Please upload a video under 100MB."
}

If upload to Supabase fails, return:
{
  "success": false,
  "message": "Video upload failed. Please try again.",
  "error_code": "SUPABASE_UPLOAD_FAILED"
}

If Gemini analysis fails, update journalist_visual_inputs.status to failed and return:
{
  "success": false,
  "message": "Video analysis failed. Please try again.",
  "error_code": "GEMINI_ANALYSIS_FAILED"
}

Do not build in this step:
- image upload
- screen recording
- live screen sharing
- live AI watching
- AI interruption during recording
- new follow-up engine
- tacit knowledge extraction
- final content generation
- vector database
- multi-file upload

Success criteria:
1. User can choose Upload Video / Screen Recording.
2. User can upload MP4, MOV, or WEBM video.
3. User can preview the uploaded video.
4. User can optionally add context.
5. User can click Analyze Video.
6. Video is uploaded to Supabase Storage.
7. Metadata is saved in journalist_visual_inputs.
8. Gemini parses the video.
9. Full analysis is saved in journalist_visual_analysis.
10. Existing follow-up flow receives the parsed analysis.
11. User sees only a short summary and first follow-up question.