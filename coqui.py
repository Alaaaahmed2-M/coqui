import tkinter as tk
from tkinter import messagebox
import threading
import os
from TTS.api import TTS
from pydub import AudioSegment

os.makedirs("tts_outputs", exist_ok=True)

tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    progress_bar=False,
    gpu=False
)

# الأصوات الحقيقية المتاحة في الموديل
available_speakers = tts.speakers

# اختاري من الموجود فعليًا فقط
male_candidates = [  
  "Andrew Chipper"
]

female_candidates = [
    "Gracie Wise"
]

# فلترة الأصوات الموجودة فعليًا
male_speakers = [s for s in male_candidates if s in available_speakers]
female_speakers = [s for s in female_candidates if s in available_speakers]

# fallback لو مفيش
if not male_speakers:
    male_speakers = [available_speakers[0]]

if not female_speakers:
    female_speakers = [available_speakers[0]]

speaker_indices = {"male": 0, "female": 0}


def get_next_speaker(gender):
    speakers = male_speakers if gender == "male" else female_speakers
    index = speaker_indices[gender]

    speaker = speakers[index]

    speaker_indices[gender] = (index + 1) % len(speakers)

    return speaker


# تقسيم النص
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


# اسم ملف تلقائي
def get_next_filename():
    i = 1
    while True:
        path = os.path.join("tts_outputs", f"final_output_{i}.wav")

        if not os.path.exists(path):
            return path

        i += 1


def convert_text_to_speech():
    text = text_input.get("1.0", tk.END).strip()

    if not text:
        messagebox.showwarning("Warning", "Please enter some text first!")
        return

    lang = lang_var.get()

    if not lang:
        messagebox.showwarning("Warning", "Please select a language!")
        return

    gender = gender_var.get()

    if not gender:
        messagebox.showwarning("Warning", "Please select gender!")
        return

    try:
        speaker = get_next_speaker(gender)

        output_path = get_next_filename()

        parts = split_text(text)

        combined_audio = AudioSegment.empty()
        temp_files = []

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

        for f in temp_files:
            segment = AudioSegment.from_wav(f)
            combined_audio += segment

        combined_audio.export(output_path, format="wav")

        # حذف الملفات المؤقتة
        for f in temp_files:
            try:
                os.remove(f)
            except:
                pass

        messagebox.showinfo(
            "Done",
            f"Voice: {speaker}\nSaved:\n{output_path}"
        )

    except Exception as e:
        messagebox.showerror("Error", str(e))


def start_conversion():
    threading.Thread(
        target=convert_text_to_speech,
        daemon=True
    ).start()


# -------- UI --------
root = tk.Tk()
root.title("Coqui XTTS - Realistic Voice Generator")
root.geometry("620x550")
root.resizable(False, False)
root.configure(bg="#f2f4f7")

title_label = tk.Label(
    root,
    text="Text-to-Speech Converter",
    font=("Arial", 18, "bold"),
    fg="#2E7D32",
    bg="#f2f4f7"
)
title_label.pack(pady=15)

tk.Label(
    root,
    text="Enter your text below:",
    font=("Arial", 12, "bold"),
    bg="#f2f4f7"
).pack(pady=5)


text_input = tk.Text(
    root,
    height=10,
    width=70,
    font=("Arial", 11),
    relief="solid",
    bd=1
)
text_input.pack(pady=10)


def paste_text(event=None):
    try:
        text_input.insert(
            tk.INSERT,
            root.clipboard_get()
        )
    except:
        pass


text_input.bind("<Control-v>", paste_text)
text_input.bind("<Control-V>", paste_text)
text_input.bind("<Button-3>", paste_text)

tk.Label(
    root,
    text="Select Language:",
    font=("Arial", 12, "bold"),
    bg="#f2f4f7"
).pack(pady=5)

lang_var = tk.StringVar(value="en")

lang_menu = tk.OptionMenu(
    root,
    lang_var,
    "ar", "en", "fr", "es",
    "de", "it", "tr", "ru", "hi"
)
lang_menu.pack(pady=5)

tk.Label(
    root,
    text="Select Gender:",
    font=("Arial", 12, "bold"),
    bg="#f2f4f7"
).pack(pady=5)

gender_var = tk.StringVar()

gender_menu = tk.OptionMenu(
    root,
    gender_var,
    "male",
    "female"
)
gender_menu.pack(pady=5)

convert_button = tk.Button(
    root,
    text="Convert Text to Speech",
    command=start_conversion,
    bg="#4CAF50",
    fg="white"
)
convert_button.pack(pady=25)

root.mainloop()