# app/services/photo_service.py

from openai import AsyncOpenAI
from app.core.config import settings
import base64
import logging

client = AsyncOpenAI(api_key=settings.openai_api_key)
logger = logging.getLogger(__name__)


class PhotoService:
    """
    Service to analyze uploaded photos and generate follow-up questions for storytelling.
    """

    async def analyze_image(self, user_id: str, file_path: str) -> str:
        """
        Analyze the photo and return a follow-up question for the user to narrate a memory.
        """
        try:
            # Read and encode image as base64
            with open(file_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = f"""
            You are a compassionate British interviewer, skilled at analyzing photos to inspire storytelling.
            The user has uploaded a meaningful photo.

            Analyze the content of the photo (represented as base64) and imagine what it could depict
            (e.g., a family gathering, childhood event, trip, friendship, celebration, etc.).

            Base64 (for model reference only): {image_b64[:500]}...

            Generate ONE thoughtful, open-ended question that encourages the user
            to tell a story or memory related to this photo.
            Respond ONLY with the question text.
            """

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a thoughtful interviewer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
            )

            question = response.choices[0].message.content.strip()
            return question

        except Exception:
            logger.exception("Failed to analyze image.")
            return "Could not generate a question from this photo."


# Singleton instance
photo_service = PhotoService()
