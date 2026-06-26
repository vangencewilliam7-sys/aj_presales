"""
Gemini Vision Service
Wraps google-generativeai SDK for analyzing images.
"""
import os
import json
import logging
import google.generativeai as genai

from prompts.visual_analysis import VISUAL_IMAGE_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

class GeminiVisionService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini features will fail.")
        else:
            genai.configure(api_key=api_key)
        
        # Using the specified model
        self.model = genai.GenerativeModel("gemini-3.5-flash")

    def analyze_image(self, file_bytes: bytes, mime_type: str, context_text: str) -> tuple[dict, str]:
        """
        Send image and context to Gemini and return structured JSON + raw response string.
        """
        logger.info("Analyzing image with Gemini Vision...")
        
        # Pass bytes to Gemini
        image_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }

        prompt = VISUAL_IMAGE_ANALYSIS_PROMPT.format(
            context_text=context_text if context_text else "(No context provided by expert)"
        )

        try:
            # We can use generation_config to force JSON response if supported,
            # but parsing standard markdown is safer across older SDK versions.
            response = self.model.generate_content([image_part, prompt])
            content = response.text.strip()
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content), response.text
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON: {content}")
            raise Exception(f"Gemini returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini analysis failed: {str(e)}")
            raise Exception(f"Failed to analyze image with Gemini: {str(e)}")

    def analyze_video(self, file_bytes: bytes, mime_type: str, context_text: str) -> tuple[dict, str]:
        """
        Send video and context to Gemini using the File API and return structured JSON + raw response string.
        """
        import tempfile
        import time
        logger.info("Analyzing video with Gemini Vision...")
        
        # We must use a local file for video uploads
        ext = ".webm" if "webm" in mime_type else ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_video_file:
            temp_video_file.write(file_bytes)
            temp_file_path = temp_video_file.name

        uploaded_file = None
        try:
            # Upload to Gemini File API
            uploaded_file = genai.upload_file(path=temp_file_path, mime_type=mime_type)
            logger.info(f"Uploaded video to Gemini: {uploaded_file.name}")

            # Wait for processing to complete
            while uploaded_file.state.name == "PROCESSING":
                logger.info("Waiting for video processing...")
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                raise Exception("Gemini video processing failed internally.")

            from prompts.visual_analysis import VISUAL_VIDEO_ANALYSIS_PROMPT
            prompt = VISUAL_VIDEO_ANALYSIS_PROMPT.format(
                context_text=context_text if context_text else "(No context provided by expert)"
            )

            response = self.model.generate_content([uploaded_file, prompt])
            content = response.text.strip()
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content), response.text

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini video JSON: {content}")
            raise Exception(f"Gemini returned invalid JSON for video: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini video analysis failed: {str(e)}")
            raise Exception(f"Failed to analyze video with Gemini: {str(e)}")
        finally:
            # Cleanup Gemini file
            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete Gemini file {uploaded_file.name}: {e}")
            
            # Cleanup local temp file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")

