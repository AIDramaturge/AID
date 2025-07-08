import os
import subprocess
import tempfile
import openai
from pathlib import Path
from PIL import Image
import streamlit as st
import cv2
import shutil
from dotenv import load_dotenv
import fitz  # PyMuPDF
import base64
import imageio_ffmpeg
import docx2txt
from io import BytesIO

# ---------------------- FUNKCIE NA SPRACOVANIE OBRAZKOV ----------------------

def extract_visual_description_with_openai(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "First, extract all readable text from the image (OCR). Then, describe the image in detail as if you were writing a scene description for a storyboard. Focus on people, actions, emotions, setting, objects, and atmosphere."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                ]}
            ],
            max_tokens=1024
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OCR Error: {e}"

# ---------------------- ENV A OPENAI ----------------------

env_path = Path(".env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

client = openai.OpenAI()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------------------- SESSION STATE ----------------------

def init_session_state():
    if "user_text" not in st.session_state:
        st.session_state.user_text = ""
    if "analysis_output" not in st.session_state:
        st.session_state.analysis_output = ""
    if "video_processed" not in st.session_state:
        st.session_state.video_processed = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

init_session_state()

# ---------------------- UI HLAVICKA ----------------------

logo = Image.open("logo_cg.png")
col1, col2 = st.columns([1, 4])
with col1:
    st.image(logo, width=400)
with col2:
    st.markdown("<h1 style='padding-top: 0px;'>AID - Artificial Intelligence Dramaturge</h1>", unsafe_allow_html=True)

st.set_page_config(page_title="AI Dramaturge", layout="wide")

# ---------------------- NAČÍTANIE PROMPTOV ----------------------

play_prompt = Path("aid_prompt_play.txt").read_text(encoding="utf-8")
storyboard_prompt = Path("aid_prompt_storyboard.txt").read_text(encoding="utf-8")

def get_prompt(input_type: str, user_text: str) -> str:
    if input_type == "Dramatic Text (TV, Movie, Theatre)":
        return f"{play_prompt.strip()}\n\nTEXT:\n{user_text.strip()}"
    else:
        return f"{storyboard_prompt.strip()}\n\nTEXT:\n{user_text.strip()}"

def analyze_text(input_type, user_text):
    full_prompt = get_prompt(input_type, user_text)
    try:
        st.session_state.chat_history = [
            {"role": "user", "content": full_prompt}
        ]
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=st.session_state.chat_history,
            temperature=0.4,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# ---------------------- VÝBER TYPU ANALÝZY ----------------------

input_type = st.radio(
    "This is an AI-powered dramaturgical analysis tool using the principles of Anglo-American dramaturgy. What are you analyzing?",
    ["Dramatic Text (TV, Movie, Theatre)", "Advertising Concept/Script (Text)", "Advertising Storyboard (Image)", "Advertising Storyboard PDF Format (Image + Text)", "Advertising TV Spot (Video 10 - 150 sec)"],
    horizontal=True
)

# ---------------------- SPRACOVANIE OBRAZKOV ZO STORYBOARDU ----------------------

if input_type == "Advertising Storyboard (Image)":
    st.markdown("### 🖼️ Upload image(s) of your storyboard")
    uploaded_files = st.file_uploader("Upload storyboard image(s):", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="image_storyboard_uploader")
    description_text = ""
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                image = Image.open(uploaded_file).convert("RGB")
                extracted = extract_visual_description_with_openai(image)
                description_text += f"\n--- From {uploaded_file.name} ---\n{extracted}\n"
            except Exception as e:
                description_text += f"\n--- Error with {uploaded_file.name} ---\n{e}"

    st.session_state.user_text = description_text.strip()
    if description_text:
        st.text_area("Extracted Description & Text from Images:", value=description_text.strip(), height=400)
    
if input_type == "Advertising Concept/Script (Text)":
    st.markdown("### ✍️ Paste or upload your concept or script (in any language)")
    st.session_state.user_text = st.text_area("Paste your concept or script here:", height=300, key="text_input")

    uploaded_txt = st.file_uploader("Or upload a .txt file:", type=["txt"])
    if uploaded_txt is not None:
        uploaded_text = uploaded_txt.read().decode("utf-8")
        st.session_state.user_text = uploaded_text.strip()

# Spracovanie storyboardu PDF s textom aj obrázkami
elif input_type == "Advertising Storyboard PDF Format (Image + Text)":
    st.markdown("### 📄 Upload your PDF storyboard (text in any language)")
    uploaded_pdf = st.file_uploader("Upload a PDF file:", type=["pdf"])
    if uploaded_pdf is not None:
        with st.spinner("🕐 I'm still transcribing the images and text into a text script. That may take some time."):
            pdf_text = ""
            ocr_text = ""
            images = []

            with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
                for page_number, page in enumerate(doc):
                # Extrahuj text
                    pdf_text += page.get_text()

                # Extrahuj obrázky
                    image_list = page.get_images(full=True)
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        try:
                            image = Image.open(BytesIO(image_bytes)).convert("RGB")
                            extracted_text = extract_visual_description_with_openai(image)
                        except Exception as e:
                            extracted_text = f"OCR Error on Page {page_number + 1}, Image {img_index + 1} ---\n{e}"

                        ocr_text += f"\n--- OCR from Page {page_number + 1}, Image {img_index + 1} ---\n{extracted_text}"

            combined_text = (pdf_text.strip() + "\n\n" + ocr_text.strip()).strip()
            st.session_state.user_text = combined_text
            st.text_area("Extracted Text + OCR", value=combined_text, height=400)

elif input_type == "Advertising TV Spot (Video 10 - 150 sec)":
    st.markdown("### 🎬 Upload a TV spot (I understand many languages, including Slovak and Czech)")
    uploaded_video = st.file_uploader("Upload a TV spot (MP4, MOV, etc.):", type=["mp4", "mov"])
    if uploaded_video and not st.session_state.video_processed:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, uploaded_video.name)
            with open(video_path, "wb") as f:
                f.write(uploaded_video.read())

            audio_path = os.path.join(tmpdir, "audio.mp3")
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run([
                ffmpeg_path, "-i", video_path,
                "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", audio_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            st.info("🎹 Transcribing audio with OpenAI API...")
            with open(audio_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                transcript = transcript_response.text.strip()

            st.info("🖼️ Extracting keyframes from video... I'm analyzing a keyframe every 2 seconds. It takes time. Sometimes a lot of time. Stay cool.")
            vidcap = cv2.VideoCapture(video_path)
            frame_count = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps
            interval = 2

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

            st.markdown("### 🖼️ Extracted Keyframes")
            cols = st.columns(3)
            col_idx = 0
            for sec in range(0, int(duration), interval):
                frame_file = os.path.join(frames_dir, f"frame_{sec}.jpg")
                if os.path.exists(frame_file):
                    image = Image.open(frame_file)
                    with cols[col_idx % 3]:
                        st.image(image, caption=f"Frame at {sec} sec", use_container_width=True)
                    col_idx += 1

            full_script = ""
            for idx, desc in enumerate(visual_descriptions):
                full_script += f"\nScene {idx + 1}:\n[Visual] {desc}\n"

            full_script += f"\n[Transcripted Audio]\n{transcript}"
            st.session_state.user_text = full_script.strip()
            st.session_state.video_processed = True
            st.success("✅ Script created. Ready for analysis. Would you like to see/edit it?")

if input_type == "Dramatic Text (TV, Movie, Theatre)":
    st.markdown("### 🎭 Paste or upload your dramatic text (in any language)")
    st.session_state.user_text = st.text_area("Paste your dramatic text here:", height=300, key="text_input")
    uploaded_play = st.file_uploader("Or upload a dramatic text file (TXT, DOCX):", type=["txt", "docx"])
    if uploaded_play is not None:
        if uploaded_play.name.endswith(".txt"):
            text = uploaded_play.read().decode("utf-8")
        elif uploaded_play.name.endswith(".docx"):
            text = docx2txt.process(uploaded_play)
        else:
            text = ""
        st.session_state.user_text = text.strip()

if st.button("Show script"):
    edited_script = st.text_area("Script Text (editable):", value=st.session_state.user_text, height=400, key="script_editor")
    if st.button("Save Changes"):
        st.session_state.user_text = edited_script
        st.success("✅ Changes saved.")

# Spustenie analýzy
if st.button("Analyze"):
    if not st.session_state.user_text.strip():
        st.warning("Please enter or upload content for analysis.")
    else:
        with st.spinner("Analyzing, please wait..."):
            result = analyze_text(input_type, st.session_state.user_text)
            st.session_state.analysis_output = result
            st.markdown("### 🔍 Analysis Result")
            st.text_area("Analysis", value=result, height=400)

# Dodatočné otázky pre AID
if st.session_state.analysis_output:
    st.markdown("### 🤖 You can continue with an additional questions or tasks for AID.")
    followup = st.text_input("Enter your question/task:")
    if followup:
        st.session_state.chat_history.append({"role": "user", "content": followup})
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=st.session_state.chat_history,
                temperature=0.4,
                max_tokens=1024
            )
            answer = response.choices[0].message.content
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.markdown("### 💬 AID's Response")
            st.write(answer)
        except Exception as e:
            st.error(f"Error: {e}")

# COPY BUTTON
copy_button = f'''
    <button onclick="navigator.clipboard.writeText(document.getElementById('analysis_copy').value)">
        Copy Analysis
    </button>
    <textarea id='analysis_copy' style='display:none;'>{st.session_state.get("analysis_output", "").replace("</", "<\/")}</textarea>
'''
st.components.v1.html(copy_button, height=50)

# CLEAR BUTTON
if st.button("❌ Clear All"):
    st.session_state.user_text = ""
    st.session_state.analysis_output = ""
    st.session_state.video_processed = False
    st.session_state.chat_history = []
    st.rerun()

# RESET VIDEO BUTTON
if input_type == "TV Spot (Video 15 - 150 sec)" and st.button("♻️ Reset Video Processing"):
    st.session_state.user_text = ""
    st.session_state.analysis_output = ""
    st.session_state.video_processed = False
    st.rerun()
