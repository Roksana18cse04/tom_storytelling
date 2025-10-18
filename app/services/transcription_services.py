#app.services.transcription.py
from openai import OpenAI
import tempfile
from app.core.config import settings

client=OpenAI(api_key= settings.openai_api_key)


async def transcribe_audio(audio_file):
    with tempfile.NamedTemporaryFile(delete= False, suffix= ".mp3") as temp_audio:
        content = await audio_file.read()
        temp_audio.write(content)
        temp_audio_path= temp_audio.name 

    transcript = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=open(temp_audio_path, "rb"),
    )

    return transcript.text    