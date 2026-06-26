"""
Visual Input Repository — Middleware for visual_inputs and visual_analysis tables.
Handles database inserts and Supabase Storage bucket uploads.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VisualInputRepo:
    def __init__(self, supabase_client):
        self._db = supabase_client
        self.bucket_name = "journalist-visual-inputs"

    def create_visual_input(self, data: dict) -> dict:
        """Create a new visual input metadata record."""
        res = self._db.table("journalist_visual_inputs").insert(data).execute()
        if not res.data:
            raise Exception("Failed to create visual input record.")
        return res.data[0]

    def update_visual_input(self, input_id: str, data: dict) -> None:
        """Update fields on a visual input record."""
        self._db.table("journalist_visual_inputs").update(data).eq("id", input_id).execute()

    def create_visual_analysis(self, data: dict) -> dict:
        """Create a new visual analysis record."""
        res = self._db.table("journalist_visual_analysis").insert(data).execute()
        if not res.data:
            raise Exception("Failed to create visual analysis record.")
        return res.data[0]

    def get_visual_analysis(self, analysis_id: str) -> dict:
        """Fetch a single analysis by ID."""
        res = self._db.table("journalist_visual_analysis").select("*").eq("id", analysis_id).execute()
        if not res.data:
            raise Exception(f"Visual analysis {analysis_id} not found.")
        return res.data[0]

    def upload_to_storage(self, path: str, file_bytes: bytes, content_type: str) -> str:
        """Upload a file to Supabase Storage and return the storage path."""
        try:
            res = self._db.storage.from_(self.bucket_name).upload(
                file=file_bytes,
                path=path,
                file_options={"content-type": content_type}
            )
            logger.info(f"Successfully uploaded image to storage path: {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to upload image to Supabase storage: {str(e)}")
            raise Exception(f"Storage upload failed: {str(e)}")
