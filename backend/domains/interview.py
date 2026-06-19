import json
import logging
from typing import Dict, Any
from fastapi import HTTPException

from domains.base import BaseDomain
from services.rag_engine import RagEngine
from repositories.knowledge_repo import KnowledgeRepo
from repositories.expert_repo import ExpertRepo
from repositories.session_repo import SessionRepo
from prompts import (
    ARCHETYPE_RULES,
    get_base_persona,
    get_archetype_rules,
    DAY_ONE_OPENER_PROMPT,
    ITERATION_SCRIPT_PROMPT,
    LIVE_COPILOT_PROMPT,
    GENERAL_SYNTHESIS_PROMPT,
    TUTOR_SYNTHESIS_PROMPT,
    HOMEWORK_GENERATOR_PROMPT,
    FLYWHEEL_BRIDGE_PROMPT,
    ARCHETYPE_CLASSIFIER_PROMPT
)

logger = logging.getLogger(__name__)

class InterviewDomain(BaseDomain):
    def __init__(self, llm, supabase):
        self.llm = llm
        self.supabase = supabase
        # Initialize Repository Middleware
        self.expert_repo = ExpertRepo(supabase)
        self.session_repo = SessionRepo(supabase)
        self.knowledge_repo = KnowledgeRepo(supabase)

    async def _get_expert(self, expert_id: str) -> Dict[str, Any]:
        return self.expert_repo.get_by_id(expert_id)

    async def intake(self, expert_id: str) -> Dict[str, Any]:
        expert = await self._get_expert(expert_id)
        
        # 1. Zero-Click Auto-Calibration: Determine Archetype
        arch_res = self.llm.invoke(ARCHETYPE_CLASSIFIER_PROMPT.format(
            domain=expert.get('domain', ''),
            title=expert.get('current_title', ''),
            short_bio=expert.get('short_bio', '')
        ))
        cleaned_arch = arch_res.content.strip()
        if "```json" in cleaned_arch:
            cleaned_arch = cleaned_arch.split("```json")[1].split("```")[0].strip()
        
        try:
            arch_data = json.loads(cleaned_arch)
            archetype = arch_data.get('archetype', 'the_tactician')
        except Exception:
            archetype = 'the_tactician'
            
        # Update the database with the chosen archetype
        self.expert_repo.update_archetype(expert_id, archetype)
        
        # Fire Day 1 Opener prompt with full expert profile
        res = self.llm.invoke(DAY_ONE_OPENER_PROMPT.format(
            expert_name=expert.get('name', ''),
            expert_title=expert.get('current_title', ''),
            expert_domain=expert.get('domain', ''),
            years_of_experience=expert.get('years_of_experience', 'Unknown'),
            short_bio=expert.get('short_bio', ''),
            target_audience=expert.get('target_audience', ''),
            stream_type=expert.get('stream_type', 'general'),
            archetype_rules=get_archetype_rules(archetype)
        ))
        
        cleaned = res.content.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            
        return json.loads(cleaned)

    async def generate_script(self, expert_id: str) -> Dict[str, Any]:
        expert = await self._get_expert(expert_id)
        
        # Fetch current accumulated profile
        accumulated_knowledge = self.expert_repo.get_profile(expert_id) or {}
        
        # Fetch curriculum blueprints if tutor
        if expert['stream_type'] == 'tutor':
            cb = self.expert_repo.get_curriculum_modules(expert_id)
            if cb:
                accumulated_knowledge['course_modules'] = cb.get('course_modules', [])
                
        # Determine iteration number
        iteration_number = self.session_repo.get_latest_iteration(expert_id)

        # Fetch open loops from homework ledger
        homework_gaps = self.session_repo.get_homework(expert_id) or {}

        accumulated_knowledge_str = json.dumps(accumulated_knowledge, indent=2)
        homework_gaps_str = json.dumps(homework_gaps, indent=2)
        
        # --- NEW RAG INTEGRATION ---
        # Fetch relevant uploaded knowledge from Supabase
        rag_engine = RagEngine(db_client=self.supabase, knowledge_repo=self.knowledge_repo)
        query = f"Presales best practices, battlecards, and strategies for {expert.get('domain', 'enterprise software')}"
        rag_context_text, _ = rag_engine.hybrid_rag_fetch(query=query, top_k=5)
        if not rag_context_text:
            rag_context_text = "(No specific uploaded knowledge found for this domain. Use general presales knowledge.)"
        
        archetype = expert.get('archetype', 'balanced')
        res = self.llm.invoke(ITERATION_SCRIPT_PROMPT.format(
            expert_name=expert.get('name', ''),
            expert_title=expert.get('current_title', ''),
            expert_domain=expert.get('domain', ''),
            years_of_experience=expert.get('years_of_experience', 'Unknown'),
            short_bio=expert.get('short_bio', ''),
            stream_type=expert.get('stream_type', 'general'),
            iteration_number=iteration_number,
            archetype_rules=get_archetype_rules(archetype),
            accumulated_knowledge_section=accumulated_knowledge_str,
            homework_gaps_section=homework_gaps_str,
            rag_knowledge_context=rag_context_text
        ))
        
        cleaned = res.content.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            
        script_data = json.loads(cleaned)
        
        # Save script to the active session
        active_session = self.session_repo.get_active_session(expert_id)
        if active_session:
            session_id = active_session["id"]
            self.session_repo.update_session(session_id, {"script": script_data})
            
        return script_data

    async def live_turn(self, session_id: str, expert_answer: str, request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        # 1. Fetch session and expert info
        session = self.session_repo.get_by_id(session_id)
        
        expert = await self._get_expert(session["expert_id"])
        archetype = expert.get('archetype', 'balanced')
        
        # Append answer to transcript
        current_transcript = session.get("raw_transcript", "")
        new_transcript = current_transcript + f"\n\n[EXPERT]: {expert_answer}"
        
        # 2. Get active script question and context from frontend
        current_script_question = (request_data or {}).get("current_script_question", "")
        if not current_script_question:
            current_script_question = "General domain exploration."
            
        active_block = (request_data or {}).get("active_block", "Block 1: Personal Origin & Persona")
        
        # 1. Fetch current running summary from database
        running_summary = session.get("running_summary", "")
        
        from backend.prompts.live_follow_up import SUMMARY_UPDATER_PROMPT
        
        # 2. Update the Running Summary with the new expert answer
        summary_res = self.llm.invoke(SUMMARY_UPDATER_PROMPT.format(
            running_summary=running_summary if running_summary else "(No summary yet)",
            expert_answer=expert_answer
        ))
        updated_summary = summary_res.content.strip()
        
        # Save the new running summary to the database immediately
        self.session_repo.update_session(session_id, {"running_summary": updated_summary})
        
        # 3. Single-pass: Intent Classification + Follow-up Generation (No dumb tangent counters!)
        copilot_res = self.llm.invoke(LIVE_COPILOT_PROMPT.format(
            active_block=active_block,
            active_script_question=current_script_question,
            running_summary=updated_summary,
            expert_answer=expert_answer,
            archetype_rules=get_archetype_rules(archetype)
        ))
        
        copilot_data = {"intent": "substantive", "follow_up": None}
        try:
            cl = copilot_res.content.strip()
            if "```json" in cl: cl = cl.split("```json")[1].split("```")[0].strip()
            copilot_data = json.loads(cl)
        except Exception:
            logger.warning("Failed to parse copilot response, defaulting to substantive.")
            
        action = "follow_tangent"
        next_question = copilot_data.get("follow_up")
        
        if copilot_data.get("intent") == "skip" or not next_question:
            action = "next_script_question"
            next_question = None  # Frontend advances teleprompter
        elif copilot_data.get("intent") == "off_topic":
            action = "redirect_to_script"
            
        # Append AI question to transcript (if we generated one)
        if next_question:
            new_transcript += f"\n\n[AI JOURNALIST]: {next_question}"
        self.session_repo.update_session(session_id, {"raw_transcript": new_transcript})
        
        return {
            "question": next_question,
            "decision": {
                "action": action, 
                "intent": copilot_data.get("intent"),
                "reasoning": copilot_data.get("internal_reasoning", "")
            }
        }

    def _build_conversation_history(self, transcript: str, max_turns: int = 3) -> str:
        """Build a sliding window of the last N HOST+EXPERT turn pairs."""
        if not transcript:
            return "(No conversation history yet)"
        
        lines = transcript.strip().split("\n")
        turns = []
        current_turn = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[EXPERT]:") or line.startswith("[AI JOURNALIST]:"):
                if current_turn:
                    turns.append("\n".join(current_turn))
                current_turn = [line]
            else:
                current_turn.append(line)
        
        if current_turn:
            turns.append("\n".join(current_turn))
        
        # Take the last N turns
        recent = turns[-max_turns:] if len(turns) > max_turns else turns
        return "\n\n".join(recent) if recent else "(No conversation history yet)"

    async def synthesize(self, session_id: str) -> Dict[str, Any]:
        session = self.session_repo.get_by_id(session_id)
        
        expert = await self._get_expert(session["expert_id"])
        iteration_number = session.get("iteration_number", 1)
        
        transcript = session.get("raw_transcript", "")
        
        # 1. General Synthesis (Applies to ALL streams) — with expert context
        gen_res = self.llm.invoke(GENERAL_SYNTHESIS_PROMPT.format(
            expert_name=expert.get('name', ''),
            expert_domain=expert.get('domain', ''),
            iteration_number=iteration_number,
            transcript=transcript
        ))
        cl_gen = gen_res.content.strip()
        if "```json" in cl_gen: cl_gen = cl_gen.split("```json")[1].split("```")[0].strip()
        general_data = json.loads(cl_gen)
        
        # Fetch existing profile
        ep = self.expert_repo.get_profile(expert["id"])
        if not ep:
            self.expert_repo.create_profile(expert["id"])
            ep = self.expert_repo.get_profile(expert["id"])
        
        # APPEND to JSONB arrays in python before updating (or could use Postgres RPC, but doing it in python is easier here)
        new_persona_traits = ep.get("persona_traits", []) + general_data.get("persona_traits", [])
        new_war_stories = ep.get("war_stories", []) + general_data.get("war_stories", [])
        new_mental_models = ep.get("mental_models", []) + general_data.get("mental_models", [])
        new_edge_cases = ep.get("edge_cases", []) + general_data.get("edge_cases", [])
        new_pattern_breaks = ep.get("pattern_breaks", []) + general_data.get("pattern_breaks", [])
        new_tacit_insights = ep.get("tacit_insights", []) + general_data.get("tacit_insights", [])
        
        update_ep = {
            "persona_traits": new_persona_traits,
            "war_stories": new_war_stories,
            "mental_models": new_mental_models,
            "edge_cases": new_edge_cases,
            "pattern_breaks": new_pattern_breaks,
            "tacit_insights": new_tacit_insights
        }
        
        # 2. Tutor Synthesis (If stream_type == 'tutor')
        tutor_data = {}
        if expert["stream_type"] == "tutor":
            tut_res = self.llm.invoke(TUTOR_SYNTHESIS_PROMPT.format(
                expert_name=expert.get('name', ''),
                expert_domain=expert.get('domain', ''),
                iteration_number=iteration_number,
                transcript=transcript
            ))
            cl_tut = tut_res.content.strip()
            if "```json" in cl_tut: cl_tut = cl_tut.split("```json")[1].split("```")[0].strip()
            tutor_data = json.loads(cl_tut)
            
            # Extract persona specifics
            update_ep["teaching_style"] = tutor_data.get("teaching_style", ep.get("teaching_style", ""))
            update_ep["linguistic_fingerprint"] = tutor_data.get("linguistic_fingerprint", ep.get("linguistic_fingerprint", {}))
            update_ep["system_prompt"] = tutor_data.get("system_prompt", ep.get("system_prompt", ""))
            
            # Upsert Curriculum Blueprints
            cb = self.expert_repo.get_curriculum(expert["id"])
            if not cb:
                self.expert_repo.create_curriculum(expert["id"], {
                    "course_modules": tutor_data.get("course_modules", [])
                })
            else:
                existing_modules = cb.get("course_modules", [])
                new_modules = tutor_data.get("course_modules", [])
                combined_modules = existing_modules + new_modules
                self.expert_repo.update_curriculum(expert["id"], {
                    "course_modules": combined_modules,
                    "iteration_last_updated": session["iteration_number"]
                })
        
        # Save updated expert profile
        self.expert_repo.update_profile(ep["id"], update_ep)
        
        session_synthesis = {"general": general_data, "tutor": tutor_data}
        self.session_repo.update_session(session_id, {
            "status": "synthesized",
            "session_synthesis": session_synthesis
        })
        
        return {"status": "success", "session_synthesis": session_synthesis}

    async def generate_homework(self, session_id: str) -> Dict[str, Any]:
        session = self.session_repo.get_by_id(session_id)
        
        expert = await self._get_expert(session["expert_id"])
        iteration_number = session.get("iteration_number", 1)
        
        transcript = session.get("raw_transcript", "")
        # Read the newly synthesized data
        session_synthesis_str = json.dumps(session.get("session_synthesis", {}), indent=2)
        
        res = self.llm.invoke(HOMEWORK_GENERATOR_PROMPT.format(
            expert_name=expert.get('name', ''),
            expert_domain=expert.get('domain', ''),
            iteration_number=iteration_number,
            transcript=transcript,
            extracted_session_data=session_synthesis_str
        ))
        cl = res.content.strip()
        if "```json" in cl: cl = cl.split("```json")[1].split("```")[0].strip()
        hw_data = json.loads(cl)
        
        self.session_repo.create_homework({
            "expert_id": session["expert_id"],
            "session_id": session_id,
            "iteration_number": iteration_number,
            "ai_open_loops": hw_data.get("ai_open_loops", [])
        })
        
        return {"status": "success", "homework": hw_data}

    async def flywheel_bridge(self, expert_id: str) -> Dict[str, Any]:
        expert = await self._get_expert(expert_id)
        archetype = expert.get('archetype', 'balanced')
        
        # Fetch latest homework
        hw = self.session_repo.get_homework(expert_id)
        if not hw:
            return {"bridge_opener": "Welcome back! What should we dive into today?", "internal_reasoning": "No homework ledger found."}
        previous_day = hw.get("iteration_number", 1)
        current_day = previous_day + 1
        
        res = self.llm.invoke(FLYWHEEL_BRIDGE_PROMPT.format(
            expert_name=expert.get('name', ''),
            expert_domain=expert.get('domain', ''),
            previous_day=previous_day,
            current_day=current_day,
            archetype_rules=get_archetype_rules(archetype),
            ai_open_loops=json.dumps(hw.get("ai_open_loops", []), indent=2),
            human_manual_notes=hw.get("human_manual_notes", "")
        ))
        cl = res.content.strip()
        if "```json" in cl: cl = cl.split("```json")[1].split("```")[0].strip()
        bridge_data = json.loads(cl)
        
        return bridge_data
