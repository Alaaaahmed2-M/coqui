from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import os
import re
from TTS.api import TTS
from pydub import AudioSegment

app = FastAPI()

# إنشاء فولدر الإخراج
os.makedirs("tts_outputs", exist_ok=True)

# تحميل الموديل
tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    progress_bar=False,
    gpu=False
)

# الأصوات المتاحة فعليًا
available_speakers = tts.speakers

# الأصوات المرشحة
male_candidates = [
    "Andrew Chipper"
]

female_candidates = [
    "Gracie Wise"
]

# فلترة الأصوات الموجودة فعليًا
male_speakers = [s for s in male_candidates if s in available_speakers]
female_speakers = [s for s in female_candidates if s in available_speakers]

# fallback
if not male_speakers:
    male_speakers = [available_speakers[0]]

if not female_speakers:
    female_speakers = [available_speakers[0]]

speaker_indices = {
    "male": 0,
    "female": 0
}


class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    gender: str = "male"


def get_next_speaker(gender):
    speakers = male_speakers if gender == "male" else female_speakers
    index = speaker_indices[gender]

    speaker = speakers[index]

    speaker_indices[gender] = (index + 1) % len(speakers)

    return speaker


def split_text(text, max_length=400, min_words=100):
    words = text.split()

    if len(words) <= min_words:
        return [text]

    parts = []
    current = []

    for word in words:
        current.append(word)

        current_text = " ".join(current)

        if len(current) >= min_words and len(current_text) >= max_length:
            parts.append(current_text)
            current = []

    if current:
        parts.append(" ".join(current))

    return parts


@app.post("/tts")
def generate_tts(request: TTSRequest):
    # تنظيف النص
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', request.text)
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Text cannot be empty"
        )

    gender = request.gender.lower()

    if gender not in ["male", "female"]:
        raise HTTPException(
            status_code=422,
            detail="Gender must be male or female"
        )

    # نخلي اللغة ديناميكية بدون قائمة ثابتة
    lang = request.language.strip().lower()

    speaker = get_next_speaker(gender)

    parts = split_text(text)

    temp_files = []

    try:
        # توليد الملفات المؤقتة
        for i, part in enumerate(parts, start=1):
            temp_file = os.path.join(
                "tts_outputs",
                f"temp_part_{i}.wav"
            )

            tts.tts_to_file(
                text=part,
                speaker=speaker,
                language=lang,
                file_path=temp_file
            )

            temp_files.append(temp_file)

        # دمج الصوت
        combined_audio = AudioSegment.empty()

        for f in temp_files:
            segment = AudioSegment.from_wav(f)
            combined_audio += segment

        # تحويل لملف داخل الذاكرة
        audio_buffer = io.BytesIO()

        combined_audio.export(
            audio_buffer,
            format="wav"
        )

        audio_buffer.seek(0)

        # إرجاع ملف الصوت نفسه
        return StreamingResponse(
            audio_buffer,
            media_type="audio/wav",
            headers={
                "Content-Disposition":
                f'attachment; filename="{speaker.replace(" ", "_")}.wav"'
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        # حذف الملفات المؤقتة
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
