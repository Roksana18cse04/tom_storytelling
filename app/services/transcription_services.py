#app.services.transcription.py
from openai import OpenAI
import tempfile
from app.core.config import settings
import os

client=OpenAI(api_key= settings.openai_api_key)


# async def transcribe_audio(audio_file):
#     with tempfile.NamedTemporaryFile(delete= False, suffix= ".mp3") as temp_audio:
#         content = await audio_file.read()
#         temp_audio.write(content)
#         temp_audio_path= temp_audio.name 

#     transcript = client.audio.transcriptions.create(
#         model="gpt-4o-mini-transcribe",
#         file=open(temp_audio_path, "rb"),
#     )

#     return transcript.text    


MIME_TO_SUFFIX = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".mp4",
    "audio/webm": ".webm",
    "audio/m4a": ".m4a",
    "audio/mpga": ".mpga",
}

async def transcribe_audio(audio_file):
    suffix = MIME_TO_SUFFIX.get(audio_file.content_type, ".wav")  # default .wav
    temp_audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
            content = await audio_file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        with open(temp_audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                response_format="text",
                timeout=60,
            )
        return transcript if isinstance(transcript, str) else transcript.text
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try: os.remove(temp_audio_path)
            except OSError: pass
