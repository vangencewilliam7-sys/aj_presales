import os
import re
import json
import logging
import httpx
import base64
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from supabase import create_client, Client
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

from domains.interview import InterviewDomain
from services.rag_engine import RagEngine
from repositories.knowledge_repo import KnowledgeRepo
from repositories.expert_repo import ExpertRepo
from repositories.session_repo import SessionRepo

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)
logger.info(f"Loading .env from: {os.path.abspath(env_path)}")

# --- MONKEY PATCH FOR SSL INTERCEPTION ---
# Disables SSL verification globally for httpx to bypass local Antivirus/VPN issues
_original_async_init = httpx.AsyncClient.__init__
def _new_async_init(self, *args, **kwargs):
    kwargs['verify'] = False
    kwargs['timeout'] = httpx.Timeout(60.0)
    _original_async_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _new_async_init

_original_sync_init = httpx.Client.__init__
def _new_sync_init(self, *args, **kwargs):
    kwargs['verify'] = False
    kwargs['timeout'] = httpx.Timeout(60.0)
    _original_sync_init(self, *args, **kwargs)
httpx.Client.__init__ = _new_sync_init
# -----------------------------------------

# Database Setup
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_DB_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Initialize Repository Middleware
expert_repo = ExpertRepo(supabase)
session_repo = SessionRepo(supabase)
knowledge_repo = KnowledgeRepo(supabase)

app = FastAPI(title="AI Journalist Platform - Backend (6-Phase Framework)")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI components
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, timeout=300)
llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=30, timeout=30)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# Domain Registry (Unified)
interview_domain = InterviewDomain(llm, supabase)

# ============================================================
# MODELS
# ============================================================

class ExpertIntakeRequest(BaseModel):
    name: str
    domain: str
    stream_type: str  # 'general' or 'tutor'
    expertise_streams: Optional[List[str]] = []
    years_of_experience: Optional[int] = 0
    short_bio: Optional[str] = None
    linkedin_url: Optional[str] = None

class LiveTurnRequest(BaseModel):
    session_id: str
    expert_answer: str
    current_script_question: Optional[str] = ""
    active_block: Optional[str] = "Block 1: Personal Origin & Persona"
    tangent_count: Optional[int] = 0

class HomeworkPutRequest(BaseModel):
    human_manual_notes: str

# ============================================================
# KNOWLEDGE HUB (RAG INGESTION)
# ============================================================

@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    source_type: str = Form("pdf_document"),
    author_or_channel: str = Form("Unknown"),
    global_summary: str = Form("Uploaded directly from UI")
):
    try:
        # 1. Save the uploaded file to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # 2. Prepare metadata
        metadata = {
            "source_type": source_type,
            "title": file.filename,
            "author_or_channel": author_or_channel,
            "url_or_identifier": file.filename,
            "global_summary": global_summary
        }
        
        # 3. Instantiate RagEngine and ingest
        rag_engine = RagEngine(db_client=supabase, knowledge_repo=KnowledgeRepo(supabase))
        result = rag_engine.ingest_to_supabase(file_path=temp_path, source_metadata=metadata, batch_size=50)
        
        # 4. Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return {"status": "success", "message": "Knowledge successfully ingested into RAG.", "details": result}
    except Exception as e:
        logger.error(f"Error in upload_knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

# ============================================================
# PHASE 2: INTAKE & SCRIPT GENERATION
# ============================================================

@app.post("/intake")
async def intake_endpoint(request: ExpertIntakeRequest):
    """Phase 2: Save expert profile and generate Day 1 Icebreaker."""
    try:
        # Insert Expert
        expert = expert_repo.create_expert({
            "name": request.name,
            "domain": request.domain,
            "stream_type": request.stream_type,
            "expertise_streams": request.expertise_streams,
            "years_of_experience": request.years_of_experience,
            "short_bio": request.short_bio,
            "linkedin_url": request.linkedin_url
        })
        
        expert_id = expert["id"]
        
        # Fire Intake domain logic to get icebreaker
        icebreaker_data = await interview_domain.intake(expert_id)
        
        # Create Iteration 1 session
        session = session_repo.create_session(expert_id, 1)
        
        logger.info(f"session created: {session}")
        
        return {
            "status": "success",
            "expert_id": expert_id,
            "session_id": session["id"],
            "icebreaker": icebreaker_data
        }
    except Exception as e:
        logger.error(f"Intake error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-script/{expert_id}")
async def generate_script_endpoint(expert_id: str):
    """Generate interview script for the current session iteration."""
    try:
        expert = expert_repo.get_by_id(expert_id)
        
        script_data = await interview_domain.generate_script(expert_id)
        return {"status": "success", "script": script_data, "expert": expert}
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# PHASE 3: LIVE INTERVIEW LOOP
# ============================================================

@app.get("/session/{session_id}")
async def get_session_endpoint(session_id: str):
    """Fetch session data including the generated script."""
    try:
        session = session_repo.get_by_id(session_id)
        return {"status": "success", "session": session}
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/live-turn")
async def live_turn_endpoint(request: LiveTurnRequest):
    """Phase 3: Classify intent and generate next conversational follow-up."""
    try:
        result = await interview_domain.live_turn(
            session_id=request.session_id,
            expert_answer=request.expert_answer,
            request_data={
                "current_script_question": request.current_script_question,
                "active_block": request.active_block,
                "tangent_count": request.tangent_count
            }
        )
        return result
    except Exception as e:
        logger.error(f"Live turn error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio via Deepgram."""
    if not DEEPGRAM_API_KEY:
        raise HTTPException(status_code=500, detail="Deepgram API key not configured.")
    try:
        audio_bytes = await audio.read()
        if not audio_bytes or len(audio_bytes) < 100:
            logger.warning(f"Empty or tiny audio received: {len(audio_bytes)} bytes")
            return {"transcript": ""}
        
        logger.info(f"Transcribing audio: {len(audio_bytes)} bytes, type={audio.content_type}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&language=en",
                headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": audio.content_type or "audio/webm"},
                content=audio_bytes,
            )
        if resp.status_code != 200:
            logger.error(f"Deepgram API error: {resp.status_code} - {resp.text[:200]}")
            raise HTTPException(status_code=502, detail=f"Deepgram API error: {resp.status_code}")
        transcript = resp.json().get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
        return {"transcript": transcript}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Transcription timed out.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {type(e).__name__}")

# ============================================================
# PHASE 4+5: POST-SESSION SYNTHESIS & HOMEWORK
# ============================================================

@app.post("/end-session/{session_id}")
async def end_session_endpoint(session_id: str):
    """Phase 4 & 5: Run extraction on full transcript and generate open loops."""
    try:
        # Mark ended_at
        session_repo.update_session(session_id, {
            "ended_at": datetime.now(timezone.utc).isoformat()
        })

        # Run Synthesis (Phase 4)
        synth_result = await interview_domain.synthesize(session_id)
        
        # Run Homework Generator (Phase 5)
        hw_result = await interview_domain.generate_homework(session_id)
        
        return {
            "status": "success",
            "message": "Session synthesized and homework generated.",
            "synthesis": synth_result["session_synthesis"],
            "homework": hw_result["homework"]
        }
    except Exception as e:
        logger.error(f"End session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/homework/{expert_id}")
async def get_homework(expert_id: str):
    """Fetch latest homework ledger for dashboard."""
    try:
        hw = session_repo.get_homework(expert_id)
        if not hw:
            return {"status": "success", "homework": None}
        return {"status": "success", "homework": hw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/homework/{homework_id}")
async def put_homework(homework_id: str, request: HomeworkPutRequest):
    """Journalist saves manual research notes."""
    try:
        session_repo.update_homework(homework_id, {
            "human_manual_notes": request.human_manual_notes,
            "status": "completed"
        })
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# PHASE 6: FLYWHEEL BRIDGE
# ============================================================

@app.post("/start-session/{expert_id}")
async def start_session_endpoint(expert_id: str):
    """Phase 6: Create new session iteration and generate trust-signal opener."""
    try:
        # Find latest iteration number
        next_iter = session_repo.get_latest_iteration(expert_id) + 1

        # Create new session
        session = session_repo.create_session(expert_id, next_iter)
        session_id = session["id"]
        
        # Fire Flywheel Bridge
        opener_data = await interview_domain.flywheel_bridge(expert_id)
        
        return {
            "status": "success",
            "session_id": session_id,
            "iteration_number": next_iter,
            "opener": opener_data
        }
    except Exception as e:
        logger.error(f"Start session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# KNOWLEDGE REPORTS (DASHBOARD)
# ============================================================

@app.get("/knowledge-report/{expert_id}")
async def get_knowledge_report(expert_id: str):
    """Returns accumulated expert profile + curriculum blueprints."""
    try:
        ep = expert_repo.get_profile(expert_id)
        cb = expert_repo.get_curriculum(expert_id)
        
        return {
            "status": "success",
            "expert_profile": ep if ep else {},
            "curriculum_blueprints": cb if cb else {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# RAG INGESTION HELPERS (KEPT AS-IS)
# ============================================================

def fetch_youtube_transcript(url: str) -> str:
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if not video_id_match:
        raise ValueError("Invalid YouTube URL")
    video_id = video_id_match.group(1)
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.fetch(video_id, languages=['en', 'hi', 'te'])
    except Exception as e:
        try:
            transcripts = api.list(video_id)
            transcript_list = transcripts.find_transcript(['en', 'hi', 'te']).fetch()
        except:
            transcripts = api.list(video_id)
            transcript_list = next(iter(transcripts)).fetch()
    full_text = " ".join([item.text for item in transcript_list])
    return full_text, video_id

async def background_ingest_documents(session_id: str, file_paths: List[str], filenames: List[str], domain: str):
    try:
        from services.rag_engine import chunk_by_characters
        for fp, fname in zip(file_paths, filenames):
            ext = os.path.splitext(fname)[1].lower()
            text = ""
            if ext == '.txt':
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.docx':
                from services.rag_engine import read_docx_file
                text = read_docx_file(fp)
            elif ext == '.pdf':
                import fitz
                doc = fitz.open(fp)
                text = "\\n".join(page.get_text() for page in doc)
            else:
                logger.warning(f"Unsupported extension: {ext}")
                continue
            
            chunks = chunk_by_characters(text)
            
            source = knowledge_repo.create_source({
                "source_type": "document",
                "title": fname,
                "global_summary": f"Uploaded document for session {session_id}",
                "author_or_channel": "User Upload"
            })
            source_id = source["id"]
            
            for c in chunks:
                emb = embeddings_model.embed_query(c["content"])
                knowledge_repo.insert_chunks([{
                    "source_id": source_id,
                    "content": c["content"],
                    "embedding": emb,
                    "location_marker": c["location_marker"]
                }])
            
            os.remove(fp)
        logger.info(f"Finished ingesting documents for {session_id}")
    except Exception as e:
        logger.error(f"Error in background ingest: {e}")

@app.post("/ingest")
async def ingest_documents_endpoint(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    domain: str = Form(...),
    user_session_id: str = Form(...)
):
    try:
        temp_paths = []
        filenames = []
        for file in files:
            fd, path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
            with os.fdopen(fd, 'wb') as f:
                shutil.copyfileobj(file.file, f)
            temp_paths.append(path)
            filenames.append(file.filename)
            
        background_tasks.add_task(background_ingest_documents, user_session_id, temp_paths, filenames, domain)
        return {"status": "success", "message": f"Processing {len(files)} files in the background."}
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/journalist/visual-input/analyze")
async def visual_input_analyze(
    session_id: str = Form(...),
    user_id: str = Form(""),
    context_text: str = Form(""),
    input_type: str = Form("image"),
    file: UploadFile = File(...)
):
    """Analyze uploaded visual input (image or screen recording)."""
    allowed_types = ["image/png", "image/jpeg", "image/webp", "video/webm", "video/mp4", "video/quicktime"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Must be PNG, JPG, WEBP, WEBM, MP4, or MOV.")
        
    # Read file bytes
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    # 250MB limit for video/image
    if file_size > 250 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 250MB.")

    return await interview_domain.visual_analyze(
        session_id=session_id,
        user_id=user_id,
        input_type=input_type,
        file_bytes=file_bytes,
        mime_type=file.content_type,
        file_name=file.filename,
        file_size=file_size,
        context_text=context_text
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9120)
