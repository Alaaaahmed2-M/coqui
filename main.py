from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import os
from TTS.api import TTS
from pydub import AudioSegment

app = FastAPI()

os.makedirs("tts_outputs", exist_ok=True)

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)

male_speakers = ["Craig Gutsy"]
female_speakers = ["Gracie Wise"]
speaker_indices = {"male": 0, "female": 0}

def get_next_speaker(gender):
    index = speaker_indices[gender]
    speakers = male_speakers if gender == "male" else female_speakers
    speaker = speakers[index]
    speaker_indices[gender] = (index + 1) % len(speakers)
    return speaker

def split_text(text, max_length=160):
    sentences = []
    while len(text) > max_length:
        split_index = text.rfind(" ", 0, max_length)
        if split_index == -1:
            split_index = max_length
        sentences.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        sentences.append(text)
    return sentences

class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    gender: str = "male"

@app.post("/tts")
def generate_tts(request: TTSRequest):
    text = request.text.strip()
    lang = request.language
    gender = request.gender.lower()

    # Validation
    if not text:
        raise HTTPException(status_code=422, detail="Text cannot be empty")
    if gender not in ["male", "female"]:
        raise HTTPException(status_code=422, detail="Gender must be 'male' or 'female'")
    supported_languages = ["ar", "en", "fr", "es", "de", "it", "tr", "ru", "hi"]
    if lang not in supported_languages:
        raise HTTPException(status_code=422, detail=f"Language must be one of {supported_languages}")

    speaker = get_next_speaker(gender)
    parts = split_text(text)
    temp_files = []

    try:
        for i, part in enumerate(parts, start=1):
            temp_file = os.path.join("tts_outputs", f"temp_part_{i}.wav")
            tts.tts_to_file(
                text=part,
                speaker=speaker,
                language=lang,
                file_path=temp_file
            )
            temp_files.append(temp_file)

        combined_audio = None
        for f in temp_files:
            segment = AudioSegment.from_wav(f)
            combined_audio = segment if combined_audio is None else combined_audio + segment

        # ✅ بدل ما نحفظ ملف، نكتب الصوت في الذاكرة مباشرة
        audio_buffer = io.BytesIO()
        combined_audio.export(audio_buffer, format="wav")
        audio_buffer.seek(0)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="{speaker.replace(" ", "_")}.wav"'
            }
        )

    finally:
        # تنظيف الملفات المؤقتة دايمًا حتى لو في error
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)