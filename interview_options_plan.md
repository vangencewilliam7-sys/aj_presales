# New Interview Options Plan
<!-- Paste your new prompt and plan requirements here! -->
Build the first version of the AI Journalist Visual Input Parser feature.

Important:
Follow-up questions, tacit knowledge extraction, and final content generation already exist in the product. Do not rebuild those. This task is only to add image/screenshot input parsing and pass the parsed context into the existing follow-up flow.

Feature name:
Image/Screenshot Upload + AI Understanding

Goal:
Allow the expert to upload an image or screenshot, add a short explanation, and send both to Gemini for visual understanding. After Gemini parses the image, the app should show only a short conversational summary and then continue into the existing follow-up interview flow.

User flow:
1. User selects "Upload Image / Screenshot".
2. User uploads an image.
3. User optionally writes an explanation/context.
4. User clicks "Analyze".
5. Backend stores the image in Supabase Storage.
6. Backend stores file metadata in Supabase Database.
7. Backend sends image + context_text to Gemini.
8. Gemini returns structured visual analysis.
9. Backend stores the full Gemini analysis internally.
10. Backend passes the analysis to the existing follow-up system.
11. Frontend displays only:
   - a short 1-2 sentence summary
   - the first follow-up question from the existing follow-up system

Do not show a detailed analysis report to the user.
Do not display separate sections like:
- Visual Summary
- Explanation Summary
- Visible Elements
- Key Observations
- Missing Context

The detailed Gemini analysis should be saved internally only.

Frontend requirements:
1. Add an "Upload Image / Screenshot" option.
2. Accept only:
   - PNG
   - JPG
   - JPEG
   - WEBP
3. Show image preview after upload.
4. Show optional context text box with placeholder:
   "Briefly explain what this image is about or what you want the AI Journalist to understand."
5. Add "Analyze Image" button.
6. On click, send multipart/form-data request to backend endpoint:
   POST /api/journalist/visual-input/analyze

Request payload:
- session_id
- user_id
- input_type = image
- context_text
- file

7. Show loading state:
   "Understanding your image..."
8. After response, display only a conversational message:
   Example:
   "Got it. This looks like a campaign dashboard where you are reviewing lead quality using lead source and conversion rate. The main idea seems to be that lead count alone is not enough.

   Why do you check lead source before looking at total lead count?"

Backend requirements:
1. Create or update endpoint:
   POST /api/journalist/visual-input/analyze

2. For this version, support only:
   input_type = image

3. Validate:
   - file exists
   - input_type is image
   - file type is PNG/JPG/JPEG/WEBP
   - file size is under 10MB
   - session_id is present

4. Upload image to Supabase Storage bucket:
   journalist-visual-inputs

Storage path format:
   {user_id}/{session_id}/{timestamp}_{file_name}

5. Insert file metadata into table:
   journalist_visual_inputs

Fields:
- session_id
- user_id
- input_type
- file_name
- file_type
- file_size
- storage_path
- context_text
- status = uploaded

6. Send image + context_text to Gemini API.

Gemini prompt:
"You are analyzing an uploaded image or screenshot for an AI Journalist.

The expert provided this context:
{{context_text}}

Your job is to understand the image and convert it into structured analysis that can be used by an existing follow-up interview system.

Analyze:
1. What is visible in the image
2. What the image appears to represent
3. What the expert may be trying to explain
4. Important visible elements, labels, charts, tables, UI sections, or text
5. Observations that may need follow-up clarification
6. Any missing context required to understand the image better

Return only valid JSON in this exact structure:

{
  "short_summary": "",
  "visual_summary": "",
  "spoken_or_text_summary": "",
  "timeline": [],
  "visible_elements": [],
  "key_observations": [],
  "missing_context": []
}

Rules:
- Do not invent facts.
- Only describe what is visible or supported by the expert context.
- If something is unclear, add it to missing_context.
- Keep the output useful for a journalist who will ask follow-up questions later.
- Since this is an image, timeline must be an empty array.
- short_summary must be 1-2 sentences only and suitable to show directly to the user."

7. Save full Gemini analysis into table:
   journalist_visual_analysis

Fields:
- session_id
- visual_input_id
- input_type
- visual_summary
- spoken_or_text_summary
- timeline_json
- visible_elements_json
- key_observations_json
- missing_context_json
- raw_gemini_response_json

8. Update journalist_visual_inputs.status to:
   parsed

9. Pass the Gemini analysis to the existing follow-up flow.

The follow-up flow should receive:
{
  "session_id": "...",
  "source_type": "visual_input",
  "input_type": "image",
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

10. Existing follow-up flow should generate the first follow-up question using this analysis.

11. Backend should return to frontend:
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

Example final user-facing output:
"Got it. This looks like a campaign dashboard where you are reviewing lead quality using lead source and conversion rate. The main idea seems to be that lead count alone is not enough.

Why do you check lead source before looking at total lead count?"

Supabase requirements:
Create bucket if not existing:
journalist-visual-inputs

Create tables if not existing:

Table 1: journalist_visual_inputs
Columns:
- id uuid primary key default gen_random_uuid()
- session_id uuid not null
- user_id uuid
- input_type text not null
- file_name text
- file_type text
- file_size bigint
- storage_path text
- context_text text
- gemini_file_id text
- status text default 'uploaded'
- created_at timestamptz default now()

Table 2: journalist_visual_analysis
Columns:
- id uuid primary key default gen_random_uuid()
- session_id uuid not null
- visual_input_id uuid references journalist_visual_inputs(id) on delete cascade
- input_type text
- visual_summary text
- spoken_or_text_summary text
- timeline_json jsonb
- visible_elements_json jsonb
- key_observations_json jsonb
- missing_context_json jsonb
- raw_gemini_response_json jsonb
- created_at timestamptz default now()

Environment variables needed:
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- GEMINI_API_KEY

Security:
- Do not expose GEMINI_API_KEY on frontend.
- Do not expose SUPABASE_SERVICE_ROLE_KEY on frontend.
- Gemini and Supabase service role calls must happen only from backend.

Error handling:
If file validation fails, return:
{
  "success": false,
  "message": "Only PNG, JPG, JPEG, or WEBP images under 10MB are supported."
}

If Gemini fails, update journalist_visual_inputs.status to failed and return:
{
  "success": false,
  "message": "Image analysis failed. Please try again.",
  "error_code": "GEMINI_ANALYSIS_FAILED"
}

Do not build in this step:
- video upload
- screen recording
- live screen sharing
- new follow-up engine
- tacit knowledge extraction
- final content generation
- vector database
- multi-file upload

Success criteria:
1. User can upload an image/screenshot.
2. User can add optional explanation.
3. Image is saved in Supabase Storage.
4. Metadata is saved in journalist_visual_inputs.
5. Gemini parses the image.
6. Full analysis is saved in journalist_visual_analysis.
7. Existing follow-up flow receives the analysis.
8. User sees only a short summary and the first follow-up question.
