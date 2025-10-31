# app/services/photo_service.py

from openai import AsyncOpenAI
from app.core.config import settings
import base64
import logging
import boto3
from botocore.exceptions import ClientError
import os
import uuid

client = AsyncOpenAI(api_key=settings.openai_api_key)
logger = logging.getLogger(__name__)

# Configure AWS S3
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)


def get_presigned_url(bucket_name: str, key: str, expiry: int = 3600):
    """
    Generate a presigned URL for S3 object (valid for 1 hour)
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expiry
        )
        return url
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


class PhotoService:
    """
    Service to analyze uploaded photos and generate follow-up questions for storytelling.
    """

    def upload_to_s3(self, file_path: str, user_id: str) -> str:
        """
        Upload image to AWS S3 and return public URL.
        """
        try:
            logger.info(f"Original file_path: {file_path}")
            # Extract extension properly - remove all trailing dots
            base_name = os.path.basename(file_path)
            # Split and get last part, remove all dots
            if '.' in base_name:
                ext_part = base_name.split('.')[-1].rstrip('.')
                file_extension = f".{ext_part}" if ext_part else ".jpg"
            else:
                file_extension = ".jpg"
            logger.info(f"Extracted extension: {file_extension}")
            s3_key = f"tom_storytelling/{user_id}/{uuid.uuid4()}{file_extension}"
            logger.info(f"Generated s3_key: {s3_key}")
            
            # Determine content type
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            content_type = content_type_map.get(file_extension.lower(), 'image/jpeg')
            
            # Upload to S3 (without ACL - using bucket policy for public access)
            s3_client.upload_file(
                file_path,
                settings.s3_bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate public URL and remove any trailing dots
            s3_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            s3_url = s3_url.rstrip('.')  # Final safeguard
            logger.info(f"Successfully uploaded to S3: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.exception(f"Failed to upload to S3: {str(e)}")
            return file_path  # Fallback to local path

    async def analyze_image(self, user_id: str, file_path: str) -> str:
        """
        Analyze the photo and return a simple, warm opening question.
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
                                "text": """You are a warm, thoughtful British interviewer helping someone capture their life story.

Analyze this photo and generate ONE comprehensive opening question that invites the user to share the full story.

Your question should:
- Acknowledge what you see in the photo
- Ask for WHO, WHAT, WHERE, WHEN, and WHICH LIFE PHASE in a natural, conversational way
- Be warm and inviting (2-3 sentences max)

Life phases to mention: childhood, teenage years, early adulthood, career/work life, family life, hobbies/adventures, or later life

Examples:
- "I can see what looks like a lovely family moment. Can you tell me who's in this photo, where and when it was taken, which phase of your life this was from, and what was happening?"
- "This looks like a special celebration. Who were you with, where was this, what phase of life were you in, and what's the story behind this moment?"
- "What a beautiful setting. Can you share who you were with, where this was, when it happened, which stage of your life this represents, and what made it memorable?"

Generate ONE comprehensive opening question that asks for WHO, WHAT, WHERE, WHEN, and WHICH LIFE PHASE:"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                temperature=0.7,
            )

            question = response.choices[0].message.content.strip()
            return question

        except Exception:
            logger.exception("Failed to analyze image.")
            return "Can you tell me about this photo?"
    
    async def generate_photo_followup(self, image_url: str, conversation_history: list, user_answer: str, followup_number: int) -> str:
        """
        Generate structured follow-up questions based on photo and user's answer.
        Follows a systematic approach: Context → Sensory → Emotional → Significance
        """
        try:
            # Clean image URL - remove trailing dots
            clean_image_url = image_url.rstrip('.')
            logger.info(f"Original image_url: {image_url}")
            logger.info(f"Cleaned image_url: {clean_image_url}")
            
            # Generate presigned URL for OpenAI to access
            bucket_name = settings.s3_bucket_name
            region = settings.aws_region
            prefix = f"https://{bucket_name}.s3.{region}.amazonaws.com/"
            
            if clean_image_url.startswith(prefix):
                s3_key = clean_image_url.replace(prefix, "")
            else:
                s3_key = clean_image_url  # fallback if already a key
            
            presigned_url = get_presigned_url(bucket_name, s3_key)
            if not presigned_url:
                raise Exception("Failed to generate presigned URL")
            
            logger.info(f"Generated presigned URL for image: {presigned_url}")
            
            # Build conversation context
            history_text = "\n".join([
                f"Q: {item['question']}\nA: {item['answer']}"
                for item in conversation_history
            ])
            
            # Analyze user's answer to extract entities
            entities_prompt = f"""Analyze this answer and identify:
- People mentioned (names, relationships)
- Places mentioned (locations, settings)
- Time references (when, what year, season)
- Emotions expressed (feelings, mood)

Answer: "{user_answer}"

List what you found (brief):"""
            
            # Determine follow-up focus based on number (structured approach)
            if followup_number == 1:
                focus_area = """First follow-up - Focus on WHO/WHAT:
- "Who is shown in this photo?"
- "Who else was there with you?"
- "What was happening in this moment?"
- Extract people, relationships, and what was occurring"""
            elif followup_number == 2:
                focus_area = """Second follow-up - Focus on WHEN/WHERE:
- "When was this taken? What year or season?"
- "Where exactly was this? Can you describe the place?"
- "What was the occasion or event?"
- Extract temporal and spatial context"""
            elif followup_number == 3:
                focus_area = """Third follow-up - Focus on SENSORY DETAILS:
- "What do you remember about that day?"
- "What did you see, hear, smell, or feel?"
- "Can you picture the atmosphere?"
- Encourage vivid sensory recall (sights, sounds, smells, textures)"""
            else:  # followup_number == 4
                focus_area = """Fourth follow-up - Focus on EMOTION and SIGNIFICANCE:
- "How did this moment feel?"
- "Why does this photo stand out to you?"
- "What made this moment special or meaningful?"
- Explore emotional resonance and personal significance
- Detect emotional language and respond empathetically
- If sadness/loss detected: "That must have been difficult. Would you like to share more, or shall we move on?"""
            
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""You are a warm, empathetic British interviewer helping capture life stories.

Photo conversation so far:
{history_text}

User's latest answer: "{user_answer}"

{focus_area}

Generate ONE specific follow-up question that:
1. Builds on what they've shared
2. Encourages deeper storytelling
3. Uses warm, British phrasing
4. Is empathetic if emotional language detected

Examples based on follow-up number:

Follow-up 1 (Who/What):
- "Who else was with you in this photo?"
- "Can you tell me about the people shown here?"
- "What was happening at this moment?"

Follow-up 2 (When/Where):
- "When was this taken? What year or season?"
- "Where exactly was this? Can you describe the place?"
- "What was the occasion?"

Follow-up 3 (Sensory):
- "What do you remember most vividly - the sights, sounds, or atmosphere?"
- "Can you picture what it looked like? What you could hear?"
- "What was the feeling in the air that day?"

Follow-up 4 (Emotional/Significance):
- "How did this moment make you feel?"
- "Why does this photo stand out in your memory?"
- "What made this moment special to you?"
- If emotional: "That must have been [difficult/joyful]. Would you like to share more?"

Generate ONE warm, specific follow-up question:"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": presigned_url}
                            }
                        ]
                    }
                ],
                temperature=0.7
            )

            followup = response.choices[0].message.content.strip()
            return followup

        except Exception:
            logger.exception("Failed to generate photo follow-up.")
            return None

    async def generate_caption(self, user_story: str, image_url: str = None) -> str:
        """
        Return Null - no caption generation.
        """
        return "Null"
    
    def _needs_depth_exploration(self, text: str, conversation_history: list = None) -> bool:
        """Check if response has enough detail or needs follow-up based on missing context."""
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Specific location keywords (cities, landmarks, specific places)
        specific_locations = ["district", "mountain", "park", "beach", "lake", "forest", "hill", 
                            "valley", "coast", "village", "town", "city", "country", "region"]
        
        # Check for specific context elements
        has_who = any(word in text_lower for word in ["friend", "family", "partner", "with", "people", "name", "leo", "sarah"])
        has_when = any(word in text_lower for word in ["year", "month", "season", "time", "when", "age", "university", "school", "2018", "2019"])
        
        # WHERE needs specific location, not just generic words
        has_specific_where = any(word in text_lower for word in specific_locations)
        
        # Sensory details (vivid descriptions)
        has_sensory = any(word in text_lower for word in ["looked", "sounded", "smelled", "saw", "heard", "view", "sunset", "sunrise", "color", "sound", "smell"])
        
        # Emotional depth
        has_emotion = any(word in text_lower for word in ["felt", "feeling", "happy", "sad", "excited", "memorable", "unforgettable", "laughed", "joy", "love"])
        
        # If conversation history exists, check cumulative context
        if conversation_history:
            history_text = " ".join([item.get("answer", "") for item in conversation_history])
            history_lower = history_text.lower()
            
            # Check what's present in entire conversation
            has_who = has_who or any(word in history_lower for word in ["friend", "family", "partner", "with", "leo", "sarah"])
            has_when = has_when or any(word in history_lower for word in ["year", "month", "season", "when", "university", "2018"])
            has_specific_where = has_specific_where or any(word in history_lower for word in specific_locations)
            has_sensory = has_sensory or any(word in history_lower for word in ["looked", "sounded", "saw", "heard", "view", "sunset"])
            has_emotion = has_emotion or any(word in history_lower for word in ["felt", "feeling", "happy", "memorable", "unforgettable"])
        
        # Very short response always needs follow-up
        if word_count < 15:
            return True
        
        # If response is rich (100+ words) with BOTH sensory AND emotional depth, accept it
        if word_count >= 100 and has_sensory and has_emotion:
            return False
        
        # Missing critical context (WHO, WHEN, or SPECIFIC WHERE)
        missing_context = not (has_who and has_when and has_specific_where)
        
        # Missing depth (sensory AND emotional detail)
        missing_depth = not (has_sensory and has_emotion)
        
        # Need follow-up if missing context OR missing depth
        return missing_context or missing_depth



# Singleton instance
photo_service = PhotoService()
