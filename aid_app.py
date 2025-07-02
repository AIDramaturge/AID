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
import fitz  # PyMuPDF
import pytesseract
import base64

# Nastavenie cesty k ffmpeg
os.environ["PATH"] += os.pathsep + r"C:\\ffmpeg\\ffmpeg-7.1.1-essentials_build\\bin"

# Načítanie .env premenných
env_path = Path(".env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Inicializácia OpenAI klienta
client = openai.OpenAI()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializácia session state
def init_session_state():
    if "user_text" not in st.session_state:
        st.session_state.user_text = ""
    if "analysis_output" not in st.session_state:
        st.session_state.analysis_output = ""
    if "video_processed" not in st.session_state:
        st.session_state.video_processed = False

init_session_state()

# Zobrazenie loga a názvu aplikácie v hlavičke
logo = Image.open("logo_cg.png")
col1, col2 = st.columns([1, 4])
with col1:
    st.image(logo, width=400)
with col2:
    st.markdown("<h1 style='padding-top: 0px;'>AI Dramaturgical Analysis Tool</h1>", unsafe_allow_html=True)

st.set_page_config(page_title="AI Dramaturge", layout="wide")

# Načítanie promptov
play_prompt = Path("aid_prompt_play.txt").read_text(encoding="utf-8")
storyboard_prompt = Path("aid_prompt_storyboard.txt").read_text(encoding="utf-8")

def get_prompt(input_type: str, user_text: str) -> str:
    if input_type == "Play":
        return f"{play_prompt.strip()}\n\nTEXT:\n{user_text.strip()}"
    elif input_type in ["Script or Storyboard (Text)", "Storyboard (Image)", "Storyboard (PDF)", "TV spot (video)"]:
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

# Výber typu vstupu
input_type = st.radio(
    "What are you analyzing?",
    ["Play", "Script or Storyboard (Text)", "Storyboard (Image)", "Storyboard (PDF)", "TV spot (video)"],
    horizontal=True
)

if input_type == "Storyboard or Script (text)":
    st.session_state.user_text = st.text_area("Paste your storyboard or script here:", height=300, key="text_input")

elif input_type == "Storyboard (PDF)":
    uploaded_pdf = st.file_uploader("Upload a PDF file:", type=["pdf"])
    if uploaded_pdf is not None:
        pdf_text = ""
        with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
            for page in doc:
                pdf_text += page.get_text()
        st.session_state.user_text = pdf_text.strip()

elif input_type == "Storyboard (image)":
    uploaded_files = st.file_uploader("Upload storyboard image(s):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    ocr_text = ""
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            extracted_text = pytesseract.image_to_string(image)
            ocr_text += f"\n--- From {uploaded_file.name} ---\n" + extracted_text
    st.session_state.user_text = ocr_text.strip()

elif input_type == "TV spot (video)":
    uploaded_video = st.file_uploader("Upload a TV spot (MP4, MOV, etc.):", type=["mp4", "mov"])
    if uploaded_video and not st.session_state.video_processed:
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
            st.info("🎙️ Transcribing audio...")
            result = model.transcribe(audio_path)
            transcript = result["text"].strip()

            st.info("🖼️ Extracting keyframes from video...")
            vidcap = cv2.VideoCapture(video_path)
            frame_count = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps
            interval = max(1, int(duration // 6))

            frames_dir = os.path.join(tmpdir, "frames")
            os.makedirs(frames_dir, exist_ok=True)

            visual_descriptions = []
            for sec in range(0, int(duration), interval):
                vidcap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
                success, image = vidcap.read()
                if success:
                    img_path = os.path.join(frames_dir, f"frame_{sec}.jpg")
                    cv2.imwrite(img_path, image)
                    with open(img_path, "rb") as img_file:
                        encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "user", "content": [
                                    {"type": "text", "text": "Describe this frame in detail like a visual script or storyboard."},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                                ]}
                            ],
                            max_tokens=500
                        )
                        visual_descriptions.append(response.choices[0].message.content.strip())

            vidcap.release()

            full_script = ""
            for idx, desc in enumerate(visual_descriptions):
                full_script += f"\nScene {idx + 1}:\n[Visual] {desc}\n"

            full_script += f"\n[Transcripted Audio]\n{transcript}"
            st.session_state.user_text = full_script.strip()
            st.session_state.video_processed = True
            st.success("✅ Script created. Ready for analysis.")

elif input_type == "Play":
    st.session_state.user_text = st.text_area("Paste your play text here:", height=300, key="text_input")

# Spustenie analýzy
if st.button("Analyze"):
    if not st.session_state.user_text.strip():
        st.warning("Please enter or upload content for analysis.")
    else:
        with st.spinner("Analyzing, please wait..."):
            result = analyze_text(input_type, st.session_state.user_text)
            st.session_state.analysis_output = result
            st.markdown("### 🔍 Analysis Result")
            st.text_area("Analysis", value=result, height=400, key="analysis_output")

# COPY BUTTON
copy_button = """
<button onclick=\"navigator.clipboard.writeText(document.getElementById('analysis_copy').value)\">📋 Copy Analysis</button>
<textarea id='analysis_copy' style='display:none;'>{}</textarea>
""".format(st.session_state.get("analysis_output", ""))

st.markdown(copy_button, unsafe_allow_html=True)

# CLEAR BUTTON
if st.button("❌ Clear All"):
    st.session_state.user_text = ""
    st.session_state.analysis_output = ""
    st.session_state.video_processed = False
    st.experimental_rerun()
