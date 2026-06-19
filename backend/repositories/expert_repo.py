"""
Expert Repository — Middleware for experts, expert_profile, and curriculum_blueprints tables.
This is the ONLY file that knows these table names exist.
"""
from typing import Dict, Any, Optional


class ExpertRepo:
    def __init__(self, supabase_client):
        self._db = supabase_client

    # =====================================================================
    # EXPERTS TABLE
    # =====================================================================
    def create_expert(self, data: dict) -> dict:
        """Insert a new expert and return the created record."""
        res = self._db.table("experts").insert(data).execute()
        if not res.data:
            raise Exception("Failed to create expert.")
        return res.data[0]

    def get_by_id(self, expert_id: str) -> dict:
        """Fetch a single expert by ID."""
        res = self._db.table("experts").select("*").eq("id", expert_id).execute()
        if not res.data:
            raise Exception(f"Expert {expert_id} not found.")
        return res.data[0]

    def update_archetype(self, expert_id: str, archetype: str) -> None:
        """Update the archetype field for an expert."""
        self._db.table("experts").update({"archetype": archetype}).eq("id", expert_id).execute()

    # =====================================================================
    # EXPERT PROFILE TABLE
    # =====================================================================
    def get_profile(self, expert_id: str) -> Optional[dict]:
        """Fetch the expert's accumulated knowledge profile."""
        res = self._db.table("expert_profile").select("*").eq("expert_id", expert_id).execute()
        return res.data[0] if res.data else None

    def create_profile(self, expert_id: str) -> dict:
        """Create an empty profile for an expert."""
        res = self._db.table("expert_profile").insert({"expert_id": expert_id}).execute()
        if not res.data:
            raise Exception(f"Failed to create profile for expert {expert_id}.")
        return res.data[0]

    def update_profile(self, profile_id: str, data: dict) -> None:
        """Update specific fields on the expert profile."""
        self._db.table("expert_profile").update(data).eq("id", profile_id).execute()

    # =====================================================================
    # CURRICULUM BLUEPRINTS TABLE
    # =====================================================================
    def get_curriculum(self, expert_id: str) -> Optional[dict]:
        """Fetch curriculum blueprints for a tutor expert."""
        res = self._db.table("curriculum_blueprints").select("*").eq("expert_id", expert_id).execute()
        return res.data[0] if res.data else None

    def get_curriculum_modules(self, expert_id: str) -> Optional[dict]:
        """Fetch only the course_modules column for a tutor expert."""
        res = self._db.table("curriculum_blueprints").select("course_modules").eq("expert_id", expert_id).execute()
        return res.data[0] if res.data else None

    def create_curriculum(self, expert_id: str, data: dict) -> dict:
        """Create a new curriculum blueprint."""
        payload = {"expert_id": expert_id, **data}
        res = self._db.table("curriculum_blueprints").insert(payload).execute()
        if not res.data:
            raise Exception(f"Failed to create curriculum for expert {expert_id}.")
        return res.data[0]

    def update_curriculum(self, expert_id: str, data: dict) -> None:
        """Update the curriculum blueprint for an expert."""
        self._db.table("curriculum_blueprints").update(data).eq("expert_id", expert_id).execute()
