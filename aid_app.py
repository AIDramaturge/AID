import os
import subprocess
import tempfile
import whisper
import openai
from pathlib import Path
from PIL import Image
import streamlit as st
import cv2
import shutil
from dotenv import load_dotenv
import base64
import pytesseract
import fitz  # PyMuPDF

# Inicializuj .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()

# Načítanie promptov
play_prompt = Path("aid_prompt_play.txt").read_text(encoding="utf-8")
storyboard_prompt = Path("aid_prompt_storyboard.txt").read_text(encoding="utf-8")

def get_prompt(input_type: str, user_text: str) -> str:
    if input_type == "Play":
        return f"{play_prompt.strip()}\n\nTEXT:\n{user_text.strip()}"
    else:
        return f"{storyboard_prompt.strip()}\n\nTEXT:\n{user_text.strip()}"

def analyze_text(input_type, user_text):
    full_prompt = get_prompt(input_type, user_text)
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.4,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Streamlit UI konfigurácia
st.set_page_config(page_title="AI Dramaturge", layout="wide")

# Hlavička s logom
logo = Image.open("logo_cg.png")
col1, col2 = st.columns([1, 4])
with col1:
    st.image(logo, width=400)
with col2:
    st.markdown("<h1 style='padding-top: 3px;'>AI Dramaturgical Analysis Tool</h1>", unsafe_allow_html=True)

# Výber vstupu
input_type = st.radio(
    "What are you analyzing?",
    ["Play", "Script or Storyboard (text)", "Storyboard (image)", "Storyboard (PDF)", "Video Upload"],
    horizontal=True
)

user_text = ""

if input_type == "Play" or input_type == "Script or Storyboard (text)":
    user_text = st.text_area("Paste your text or storyboard here:", height=300)

elif input_type == "Storyboard (image)":
    uploaded_files = st.file_uploader("Upload storyboard image(s):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    ocr_text = ""
    for uploaded_file in uploaded_files:
        if uploaded_file:
            image = Image.open(uploaded_file)
            ocr_text += f"\n--- From {uploaded_file.name} ---\n" + pytesseract.image_to_string(image)
    user_text = ocr_text.strip()

elif input_type == "Storyboard (PDF)":
    uploaded_pdf = st.file_uploader("Upload a PDF file:", type=["pdf"])
    if uploaded_pdf:
        with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
            user_text = "".join([page.get_text() for page in doc])

elif input_type == "Video Upload":
    uploaded_video = st.file_uploader("Upload a TV spot (MP4, MOV, etc.)", type=["mp4", "mov"])
    if uploaded_video:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, uploaded_video.name)
            with open(video_path, "wb") as f:
                f.write(uploaded_video.read())

            audio_path = os.path.join(tmpdir, "audio.wav")
            ffmpeg_path = r"C:\\ffmpeg\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"
            subprocess.run([
                ffmpeg_path, "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            model = whisper.load_model("base")
            st.info("\U0001F3A4 Transcribing audio...")
            result = model.transcribe(audio_path)
            transcript = result["text"].strip()

            st.info("\U0001F5BC️ Extracting keyframes from video...")
            vidcap = cv2.VideoCapture(video_path)
            frame_count = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps
            interval = max(1, int(duration // 6))

            frames_dir = os.path.join(tmpdir, "frames")
            os.makedirs(frames_dir, exist_ok=True)

            keyframes = []
            for sec in range(0, int(duration), interval):
                vidcap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
                success, image = vidcap.read()
                if success:
                    img_path = os.path.join(frames_dir, f"frame_{sec}.jpg")
                    cv2.imwrite(img_path, image)
                    keyframes.append(img_path)

            vidcap.release()

            visual_descriptions = []
            for frame in keyframes:
                with open(frame, "rb") as img_file:
                    encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
                    st.image(Image.open(frame), caption=f"Frame: {os.path.basename(frame)}")
                    st.info("Describing visual content with GPT-4o...")

                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this frame in detail like a visual script or storyboard."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                            ]
                        }],
                        max_tokens=500
                    )
                    visual_descriptions.append(response.choices[0].message.content.strip())

            full_script = ""
            for idx, desc in enumerate(visual_descriptions):
                full_script += f"\nScene {idx + 1}:\n[Visual] {desc}\n"
            full_script += f"\n[Transcripted Audio]\n{transcript}"
            user_text = full_script
            st.text_area("Drafted Script", value=full_script, height=400)

# ANALÝZA
if st.button("Analyze"):
    if not user_text.strip():
        st.warning("Please enter or upload content for analysis.")
    else:
        with st.spinner("Analyzing, please wait..."):
            result = analyze_text(input_type, user_text)
            st.markdown("### \U0001F50D Analysis Result")
            st.write(result)
            analysis_text = result
else:
    analysis_text = "Your analysis goes here"

st.text_area("Analysis", value=analysis_text, height=400)

# Kopírovanie výstupu
copy_button = f"""
<button onclick="navigator.clipboard.writeText(`{analysis_text}`)">\U0001F4CB Copy Analysis</button>
"""
st.markdown(copy_button, unsafe_allow_html=True)

# Reset
if st.button("\u274C Clear"):
    st.experimental_rerun()
