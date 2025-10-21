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

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "You are a compassionate British interviewer. Analyze this photo and generate ONE thoughtful, open-ended question that encourages the user to tell a story or memory related to it. Respond ONLY with the question text."
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                temperature=0.6,
            )

            question = response.choices[0].message.content.strip()
            return question

        except Exception:
            logger.exception("Failed to analyze image.")
            return "Could not generate a question from this photo."

    async def generate_caption(self, user_story: str, file_path: str = None) -> str:
        """
        Generate a concise caption for the photo based on user's story.
        """
        try:
            if file_path:
                with open(file_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")
                
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Analyze this photo and the user's story to generate a SHORT, meaningful caption (max 10-15 words). Include key details like year, people, place, or event if mentioned.\n\nUser's story: {user_story}\n\nGenerate ONLY the caption text."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                                }
                            ]
                        }
                    ],
                    temperature=0.5,
                )
            else:
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "user", "content": f"Generate a SHORT caption (max 10-15 words) based on this story: {user_story}"}
                    ],
                    temperature=0.5,
                )

            caption = response.choices[0].message.content.strip()
            return caption

        except Exception:
            logger.exception("Failed to generate caption.")
            return "Untitled memory"



# Singleton instance
photo_service = PhotoService()
