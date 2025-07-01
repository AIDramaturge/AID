import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import openai

# Načítanie .env premenných
env_path = Path(".env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Inicializácia OpenAI klienta
client = openai.OpenAI()

# Načítanie promptov
play_prompt = Path("aid_prompt_play.txt").read_text(encoding="utf-8")
storyboard_prompt = Path("aid_prompt_storyboard.txt").read_text(encoding="utf-8")

def get_prompt(input_type: str, user_text: str) -> str:
    if input_type == "Play":
        return f"{play_prompt.strip()}\n\nTEXT:\n{user_text.strip()}"
    elif input_type in ["Storyboard or Script (text)", "Storyboard (image)", "Storyboard (PDF)"]:
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

# Streamlit UI
st.set_page_config(page_title="AI Dramaturge", layout="wide")
st.title("\U0001F3AD AI Dramaturgical Analysis Tool")

input_type = st.radio(
    "What are you analyzing?",
    ["Play", "Storyboard or Script (text)", "Storyboard (image)", "Storyboard (PDF)"],
    horizontal=True
)

user_text = ""

if input_type in ["Play", "Storyboard or Script (text)"]:
    user_text = st.text_area("Paste your text or storyboard here:", height=300)

elif input_type == "Storyboard (image)":
    uploaded_files = st.file_uploader("Upload storyboard image(s):", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    ocr_text = ""
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            extracted_text = pytesseract.image_to_string(image)
            ocr_text += f"\n--- From {uploaded_file.name} ---\n" + extracted_text
    user_text = ocr_text.strip()

elif input_type == "Storyboard (PDF)":
    uploaded_pdf = st.file_uploader("Upload a PDF file:", type=["pdf"])
    if uploaded_pdf is not None:
        pdf_text = ""
        with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
            for page in doc:
                pdf_text += page.get_text()
        user_text = pdf_text.strip()

if st.button("Analyze"):
    if not user_text.strip():
        st.warning("Please enter or upload content for analysis.")
    else:
        with st.spinner("Analyzing, please wait..."):
            result = analyze_text(input_type, user_text)
            st.markdown("### \U0001F50D Analysis Result")
            st.write(result)
