import os
import subprocess
import tempfile
import openai
from pathlib import Path
from PIL import Image
import streamlit as st
import shutil
from dotenv import load_dotenv
import fitz  # PyMuPDF
import base64
import imageio_ffmpeg
import docx2txt
from io import BytesIO
import time
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import re
import streamlit.components.v1 as components

# Konfigurácia stránky MUSÍ byť prvá
st.set_page_config(page_title="AI Dramaturge", layout="wide")

# Flag pre clear
if "clear_all_triggered" not in st.session_state:
    st.session_state.clear_all_triggered = False

# Clear all logika na začiatku
if st.session_state.get("clear_all_triggered", False):
    # Zálohuj jazyk aj input_type z rádio tlačidla
    lang_backup = st.session_state.get("aid_selected_language", "sk")
    input_type_backup = st.session_state.get("input_type_selector", "Dramatic Text (TV, Movie, Theatre)")

    # Vymaž všetko
    st.session_state.clear()

    # Obnov hodnoty
    st.session_state.aid_selected_language = lang_backup
    st.session_state.current_input_type = input_type_backup
    st.session_state.input_type_selector = input_type_backup
    st.session_state.clear_all_triggered = False

    # Vyčisti cache a obnov render
    st.cache_data.clear()
    st.rerun()
# ---------------------- LOKALIZÁCIA ----------------------
LANGUAGES = {
    "en": {
        "title": "AID - Artificial Intelligence Dramaturge",
        "select_language": "Select App Language",
        "analysis_type_label": "This is an AI-powered dramaturgical analysis tool using the principles of Anglo-American dramaturgy. What are you analyzing?",
        "upload_images": "Upload storyboard image(s):",
        "upload_images here": "Upload images here",
        "upload_text": "Paste or upload your concept or script (in any language)",
        "paste_text": "Paste text",
        "upload_text file": "Upload text file",
        "upload_pdf": "Upload your storyboard as a PDF (with text and images, any language)",
        "upload_pdf here": "Upload PDF file",
        "upload_video": "Upload a video file or paste a video URL (e.g., YouTube, Vimeo). AID uderstands multiple languages.",
        "only upload_video": "Upload a video file",
        "video_url": "Paste a video URL to analyze:",
        "video_warning": "Warning: In certain cases — such as local cultural references, minimalist acting, metaphor-heavy scenes, limited intelligible lyrics, or the presence of celebrities (which AID cannot recognize) — the transcription and interpretation of the video into a script may be inaccurate. If the resulting synopsis seems incorrect after analysis, please manually enter the correct one into the text field (labeled \"Continue...\") and request a new analysis. To do this, start your prompt with: `Analyze again. Correct synopsis:....` You may write synopsis in any language. 🧠 Remember: AID functions as a dramaturge, not a competition judge. It evaluates narrative principles and structural elements based on the provided content. As such, its assessments may differ — sometimes significantly — from those of human juries. It is also not immune to error. To reduce such errors, you can repeat the analysis several times and compare the results — or write and manually submit a deep, detailed synopsis.",
        "error_file_size": "File {name} is too large ({size:.2f} MB). Maximum allowed size is {max_size} MB.",
        "error_invalid_url": "Invalid video URL. Please provide a valid YouTube or Vimeo URL.",
        "error_no_content": "Please enter or upload content for analysis.",
        "error_api_key": "OpenAI API key is missing. Please set it in the .env file.",
        "error_pdf": "Failed to process PDF: {error}",
        "error_video_download": "Failed to download video: {error}",
        "success_video_download": "Video downloaded successfully from URL. Processing now...",
        "success_script_created": "Script created. Ready for analysis. Would you like to review or edit it first? Click Show script, then Analyze. Or if you're ready, just click Analyze.",
        "success_changes_saved": "Changes saved.",
        "processing_images": "Processing {count} images. Estimated time: ~{time} seconds...",
        "processing_completed": "Processing completed in {time:.2f} seconds.",
        "show_script": "Show script",
        "save_changes": "Save Changes",
        "analyze": "Analyze",
        "Send Follow-up Question": "Send Follow-up Question",
        "Show QA history":  "Show QA history",
        "clear_all": "Clear All",
        "reset_video": "Reset Video Processing",
        "continue_prompt": "Continue. Add more questions or tasks for AID as needed.",
        "enter_question": "Enter your question/task:",
        "extracted_description": "Extracted Description & Text from Images:",
        "extracted_text_ocr": "Extracted Text + OCR",
        "analysis_result": "Analysis Result",
        "aid_response": "AID's Response",
        "paste_dramatic_text": "Paste your dramatic text here:",
        "upload_dramatic_text": "Or upload a dramatic text file (TXT, DOCX, PDF):",
        "error_unsupported_format": "Unsupported file format. Please upload .txt, .docx, or .pdf."
    },
    "sk": {
        "title": "AID - Artificial Intelligence Dramaturge",
        "select_language": "Vyberte jazyk",
        "analysis_type_label": "AID je nástroj na dramaturgickú analýzu poháňaný umelou inteligenciou, ktorý využíva princípy anglo-americkej dramaturgie. Čo chcete analyzovať?",
        "upload_images": "Nahrajte obrázky storyboardu:",
        "upload_images here": "Tu nahrajte obrázky",
        "upload_text": "Vložte alebo nahrajte váš námet/ideu, alebo scenár (v akomkoľvek jazyku)",
        "paste_text": "Vložte text",
        "upload_text file": "Nahrajte textový súbor",
        "upload_pdf": "Nahrajte váš storyboard vo formáte PDF (s textom a obrázkami, v akomkoľvek jazyku)",
        "upload_pdf here": "Nahrajte PDF súbor",
        "upload_video": "Nahrajte video súbor alebo vložte URL adresu videa (napr. z YouTube, Vimeo). AID rozumie mnohým jazykom.",
        "only upload_video": "Nahrajte video súbor",
        "video_url": "Vložte URL adresu videa na analýzu:",
        "video_warning": "Upozornenie: V niektorých prípadoch — ako je lokálny kultúrny kontext, minimalistické herectvo, scény so zložitými metaforami, obmedzene zrozumiteľný text piesní alebo prítomnosť celebrít (ktoré AID nedokáže rozpoznať) — môže byť transkripcia a interpretácia videa do scenára nepresná. Ak sa výsledná synopsa po analýze zdá nesprávna, napíšte prosím správnu synopsu manuálne do textového poľa (označeného ako „Pokračovať...“) a požiadajte o novú analýzu. Začnite svoju požiadavku slovami: `Analyzuj znova. Správna synopsa:....` Synopsu môžete napísať v akomkoľvek jazyku. 🧠 Pamätajte: AID funguje ako dramaturg, nie ako porotca súťaže. Hodnotí naratívne princípy a štrukturálne prvky na základe poskytnutého obsahu. Jeho hodnotenia sa preto môžu — niekedy výrazne — líšiť od hodnotení porôt, v ktorých hodnotia ľudia. Nie je ani imúnny voči chybám. Na zníženie rizika chýb môžete analýzu zopakovať viackrát a porovnať výsledky — alebo napísať a manuálne odoslať podrobnú synopsu.",
        "error_file_size": "Súbor {name} je príliš veľký ({size:.2f} MB). Maximálna povolená veľkosť je {max_size} MB.",
        "error_invalid_url": "Neplatná URL adresa videa. Zadajte prosím platnú URL adresu YouTube alebo Vimeo, etc.",
        "error_no_content": "Zadajte alebo nahrajte obsah na analýzu.",
        "error_api_key": "Chýba OpenAI API kľúč. Nastavte ho prosím v súbore .env.",
        "error_pdf": "Nepodarilo sa spracovať PDF: {error}",
        "error_video_download": "Nepodarilo sa stiahnuť video: {error}",
        "success_video_download": "Video bolo úspešne stiahnuté z URL. Spracováva sa...",
        "success_script_created": "Scenár bol vytvorený. Je pripravený na analýzu. Ak ho chcete najprv skontrolovať alebo upraviť, kliknite na Zobraziť scenár, po úprave na Uložiť zmeny a potom na Analyzovať. Alebo, ak nič upravovať nechcete, kliknite na Analyzovať.",
        "success_changes_saved": "Zmeny uložené.",
        "processing_images": "Spracováva sa {count} obrázkov. Odhadovaný čas: ~{time} sekúnd...",
        "processing_completed": "Spracovanie dokončené za {time:.2f} sekúnd.",
        "show_script": "Zobraziť scenár",
        "save_changes": "Uložiť zmeny",
        "analyze": "Analyzovať",
        "Send Follow-up Question": "Odoslať",
        "Show QA history": "Zobraziť históriu otázok a odpovedí",
        "clear_all": "Vymazať všetko",
        "reset_video": "Obnoviť spracovanie videa",
        "continue_prompt": "Pokračovať. Pridajte ďalšie otázky alebo úlohy pre AID podľa potreby.",
        "enter_question": "Zadajte svoju otázku/úlohu:",
        "extracted_description": "Extrahovaný popis a text z obrázkov:",
        "extracted_text_ocr": "Extrahovaný text + OCR",
        "analysis_result": "Výsledok analýzy",
        "aid_response": "Odpoveď AID",
        "paste_dramatic_text": "Vložte váš dramatický text tu:",
        "upload_dramatic_text": "Alebo nahrajte súbor s dramatickým textom (TXT, DOCX, PDF):",
        "error_unsupported_format": "Nepodporovaný formát súboru. Nahrajte prosím .txt, .docx alebo .pdf."
    },
    "cs": {
  "title": "AID - Artificial Intelligence Dramaturge",
  "select_language": "Zvolte jazyk",
  "analysis_type_label": "AID je nástroj pro dramaturgickou analýzu poháněný umělou inteligencí, který využívá principy angloamerické dramaturgie. Co si přejete analyzovat?",
  "upload_images": "Nahrajte obrázky storyboardu:",
  "upload_images here": "Nahrajte obrázky zde",
  "upload_text": "Vložte nebo nahrajte svůj námět, nápad nebo scénář (v jakémkoli jazyce)",
  "paste_text": "Vložte text",
  "upload_text file": "Nahrajte textový soubor",
  "upload_pdf": "Nahrajte storyboard ve formátu PDF (s textem a obrázky, v jakémkoli jazyce)",
  "upload_pdf here": "Nahrajte soubor PDF",
  "upload_video": "Nahrajte video soubor nebo vložte URL adresu videa (např. z YouTube nebo Vimeo). AID rozumí mnoha jazykům.",
  "only upload_video": "Nahrajte video soubor",
  "video_url": "Vložte URL adresu videa k analýze:",
  "video_warning": "Upozornění: V některých případech — jako je lokální kulturní kontext, minimalistické herectví, scény se složitými metaforami, obtížně srozumitelný zpěv nebo přítomnost celebrit (které AID nedokáže rozpoznat) — může být přepis a interpretace videa do scénáře nepřesná. Pokud se výsledná synopse po analýze jeví jako nesprávná, napište prosím správnou synopsi ručně do textového pole (označeného jako „Pokračovat...“) a požádejte o novou analýzu. Začněte svou žádost slovy: `Analyzuj znovu. Správná synopse:....` Synopsi můžete napsat v jakémkoli jazyce. 🧠 Pamatujte: AID funguje jako dramaturg, nikoli jako porotce soutěže. Hodnotí narativní principy a strukturální prvky na základě poskytnutého obsahu. Jeho hodnocení se proto může — někdy výrazně — lišit od hodnocení porot tvořených lidmi. Není ani imunní vůči chybám. Pro snížení rizika chyb můžete analýzu zopakovat vícekrát a porovnat výsledky — nebo napsat a ručně odeslat podrobnou synopsi.",
  "error_file_size": "Soubor {name} je příliš velký ({size:.2f} MB). Maximální povolená velikost je {max_size} MB.",
  "error_invalid_url": "Neplatná URL adresa videa. Zadejte prosím platnou adresu YouTube nebo Vimeo.",
  "error_no_content": "Zadejte nebo nahrajte obsah k analýze.",
  "error_api_key": "Chybí OpenAI API klíč. Nastavte jej prosím v souboru .env.",
  "error_pdf": "Nepodařilo se zpracovat PDF: {error}",
  "error_video_download": "Nepodařilo se stáhnout video: {error}",
  "success_video_download": "Video bylo úspěšně staženo z URL. Pracuje se na jeho zpracování...",
  "success_script_created": "Scénář byl vytvořen. Je připraven k analýze. Pokud si jej přejete nejprve zkontrolovat nebo upravit, klikněte na Zobrazit scénář, poté na Uložit změny a nakonec na Analyzovat. Pokud úpravy nechcete provádět, klikněte rovnou na Analyzovat.",
  "success_changes_saved": "Změny byly uloženy.",
  "processing_images": "Zpracovává se {count} obrázků. Odhadovaný čas: ~{time} sekund...",
  "processing_completed": "Zpracování dokončeno za {time:.2f} sekund.",
  "show_script": "Zobrazit scénář",
  "save_changes": "Uložit změny",
  "analyze": "Analyzovat",
  "Send Follow-up Question": "Odeslat doplňující otázku",
  "Show QA history": "Zobrazit histórii otázek a odpovědí",
  "clear_all": "Vymazat vše",
  "reset_video": "Resetovat zpracování videa",
  "continue_prompt": "Pokračujte. Přidejte další otázky nebo úkoly pro AID podle potřeby.",
  "enter_question": "Zadejte svou otázku nebo úkol:",
  "extracted_description": "Extrahovaný popis a text z obrázků:",
  "extracted_text_ocr": "Extrahovaný text + OCR",
  "analysis_result": "Výsledek analýzy",
  "aid_response": "Odpověď AID",
  "paste_dramatic_text": "Vložte svůj dramatický text zde:",
  "upload_dramatic_text": "Nebo nahrajte soubor s dramatickým textem (TXT, DOCX, PDF):",
  "error_unsupported_format": "Nepodporovaný formát souboru. Nahrajte prosím .txt, .docx nebo .pdf."
}
}
# Inicializuj jazyk ak ešte nie je
if "aid_selected_language" not in st.session_state:
   st.session_state.aid_selected_language = "en"

# Použij aktuálny jazyk
lang = st.session_state.aid_selected_language

# ---------------------- ENV A OPENAI ----------------------
env_path = Path(".env")
if env_path.exists():
   load_dotenv(dotenv_path=env_path)

if not os.getenv("OPENAI_API_KEY"):
   st.error(LANGUAGES[lang]["error_api_key"])
   st.stop()

client = openai.OpenAI()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------------------- SESSION STATE ----------------------
def init_session_state():
   """Initializes session state variables if they don't exist."""
   defaults = {
       "aid_user_text": "",
       "aid_analysis_output": "",
       "aid_video_processed": False,
       "aid_chat_history": [],
       "aid_show_script": False,
       "aid_uploaded_video": None,
       "aid_script_created": False,
       "aid_storyboard_processed_text": None,
       "aid_storyboard_file_name": None,
       "aid_image_processing_done": False,
       "aid_image_processing_key": 0
   }
   
   for key, default_value in defaults.items():
       if key not in st.session_state:
           st.session_state[key] = default_value

init_session_state()

# ---------------------- FUNKCIE NA KONTROLU SÚBOROV A URL ----------------------
def check_file_size(file, max_size_mb=10) -> bool:
   """Checks if the file size is within the allowed limit."""
   file_size_mb = len(file.getvalue()) / (1024 * 1024)
   if file_size_mb > max_size_mb:
       st.error(LANGUAGES[lang]["error_file_size"].format(name=file.name, size=file_size_mb, max_size=max_size_mb))
       return False
   return True

def is_valid_url(url: str) -> bool:
   """Validates if the provided URL is a valid YouTube or Vimeo URL."""
   regex = r'^(https?://)?(www\.)?(youtube\.com|vimeo\.com)/.+$'
   return re.match(regex, url) is not None

# ---------------------- FUNKCIE NA SPRACOVANIE OBRAZKOV ----------------------
def compress_image(image: Image.Image, max_size=(1024, 1024)) -> Image.Image:
   """Compresses an image to reduce its size while maintaining quality."""
   image.thumbnail(max_size, Image.Resampling.LANCZOS)
   return image

def extract_visual_description_with_openai(image: Image.Image) -> str:
   """Extracts text and visual description from an image using OpenAI's GPT-4o model."""
   image = compress_image(image)
   buffered = BytesIO()
   image.save(buffered, format="JPEG", quality=85)
   img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

   if len(img_str) > 5_000_000:
       return "Error: Image is too large after encoding."

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

# ---------------------- UI HLAVICKA ----------------------
# Výber jazyka
lang = st.selectbox(
   LANGUAGES[st.session_state.aid_selected_language]["select_language"],
   options=["sk", "en", "cs"],
   format_func=lambda x: {"sk": "Slovenčina", "en": "English", "cs": "Čeština"}.get(x, x),
   key="language_selector",
   index=["sk", "en", "cs"].index(st.session_state.aid_selected_language)
)
if lang != st.session_state.aid_selected_language:
   st.session_state.aid_selected_language = lang
   st.rerun()

logo = Image.open("logo_cg.png")
col1, col2 = st.columns([1, 4])
with col1:
   st.image(logo, width=400)
with col2:
   st.markdown(f"<h1 style='padding-top: 0px;'>{LANGUAGES[lang]['title']}</h1>", unsafe_allow_html=True)

# ---------------------- NAČÍTANIE PROMPTOV ----------------------
play_prompt = Path("aid_prompt_play.txt").read_text(encoding="utf-8")
storyboard_prompt = Path("aid_prompt_storyboard.txt").read_text(encoding="utf-8")

def get_prompt(input_type: str, user_text: str, lang: str = "en") -> str:
    """Generates a prompt based on input type and user text, with language control."""
    if input_type == "Dramatic Text (TV, Movie, Theatre)":
        base_prompt = play_prompt.strip()
    else:
        base_prompt = storyboard_prompt.strip()

    language_instruction = ""
    if lang == "sk":
        language_instruction = "Odpovedz prosím výhradne v slovenčine.\n"

    return f"{language_instruction}{base_prompt}\n\nTEXT:\n{user_text.strip()}"

def analyze_text(input_type: str, user_text: str) -> str:
   """Analyzes text using OpenAI's GPT-4-turbo model."""
   full_prompt = get_prompt(input_type, user_text, lang)
   try:
       st.session_state.aid_chat_history = [
           {"role": "user", "content": full_prompt}
       ]
       response = client.chat.completions.create(
           model="gpt-4o",
           messages=st.session_state.aid_chat_history,
           temperature=0.4,
           max_tokens=8192
       )
       return response.choices[0].message.content
   except Exception as e:
       return f"Error: {e}"

# ---------------------- VÝBER TYPU ANALÝZY ----------------------
input_type = st.radio(
   LANGUAGES[lang]["analysis_type_label"],
   [
       "Advertising Concept/Script (Text)",
       "Advertising Storyboard (Image)",
       "Advertising Storyboard PDF Format (Image + Text)",
       "TV Commercial (Video 10 - 150 sec)",
       "Dramatic Text (TV, Movie, Theatre)"
   ],
   horizontal=True,
   key="input_type_selector"
)
# Uložte aktuálny typ
st.session_state.current_input_type = input_type

# ---------------------- SPRACOVANIE OBRAZKOV ZO STORYBOARDU ----------------------
if input_type == "Advertising Storyboard (Image)":
   st.markdown(f"### 🖼️ {LANGUAGES[lang]['upload_images']}")
   
   # Použitie jedinečného kľúča pre file uploader
   uploader_key = f"image_uploader_{st.session_state.aid_image_processing_key}"
   
   uploaded_files = st.file_uploader(
       LANGUAGES[lang]["upload_images here"],
       type=["png", "jpg", "jpeg"],
       accept_multiple_files=True,
       key=uploader_key
   )

   description_text = ""

   if uploaded_files and not st.session_state.aid_image_processing_done:
       MAX_IMAGES = 60
       if len(uploaded_files) > MAX_IMAGES:
           st.warning(f"⚠️ Too many images ({len(uploaded_files)}). Processing only the first {MAX_IMAGES}.")
           uploaded_files = uploaded_files[:MAX_IMAGES]

       start_time = time.time()
       with st.spinner(LANGUAGES[lang]["processing_images"].format(count=len(uploaded_files), time=len(uploaded_files) * 2)):
           for uploaded_file in uploaded_files:
               if not check_file_size(uploaded_file):
                   continue
               try:
                   image = Image.open(uploaded_file).convert("RGB")
                   extracted = extract_visual_description_with_openai(image)
                   description_text += f"\n--- From {uploaded_file.name} ---\n{extracted}\n"
               except Exception as e:
                   description_text += f"\n--- Error with {uploaded_file.name} ---\n{e}"
           st.success(LANGUAGES[lang]["processing_completed"].format(time=time.time() - start_time))

       st.session_state.aid_user_text = description_text.strip()
       st.session_state.aid_image_processing_done = True
       
   if st.session_state.aid_user_text and input_type == "Advertising Storyboard (Image)":
       st.text_area(LANGUAGES[lang]["extracted_description"], value=st.session_state.aid_user_text, height=400)

# ---------------------- SPRACOVANIE TEXTU ----------------------
elif input_type == "Advertising Concept/Script (Text)":
   st.markdown(f"### ✍️ {LANGUAGES[lang]['upload_text']}")
   st.session_state.aid_user_text = st.text_area(LANGUAGES[lang]["paste_text"], height=300, key="text_input")

   uploaded_txt = st.file_uploader(LANGUAGES[lang]["upload_text file"], type=["txt"])
   if uploaded_txt is not None:
       if not check_file_size(uploaded_txt):
           st.stop()
       uploaded_text = uploaded_txt.read().decode("utf-8")
       st.session_state.aid_user_text = uploaded_text.strip()

# ---------------------- SPRACOVANIE PDF ----------------------
elif input_type == "Advertising Storyboard PDF Format (Image + Text)":
   st.markdown(f"### 📄 {LANGUAGES[lang]['upload_pdf']}")
   uploaded_pdf = st.file_uploader(LANGUAGES[lang]["upload_pdf here"], type=["pdf"])

   if uploaded_pdf is not None:
       if not check_file_size(uploaded_pdf):
           st.stop()
       if "aid_storyboard_processed_text" not in st.session_state or st.session_state.get("aid_storyboard_file_name") != uploaded_pdf.name:
           with tempfile.TemporaryDirectory() as tmpdir:
               try:
                   start_time = time.time()
                   pdf_text = ""
                   image_tasks = []
                   MAX_IMAGES = 60

                   try:
                       with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
                           for page_number, page in enumerate(doc):
                               pdf_text += page.get_text()
                               image_list = page.get_images(full=True)
                               for img_index, img in enumerate(image_list):
                                   if len(image_tasks) >= MAX_IMAGES:
                                       st.warning(f"⚠️ Too many images ({len(image_list)}). Processing only the first {MAX_IMAGES}.")
                                       break
                                   xref = img[0]
                                   base_image = doc.extract_image(xref)
                                   image_bytes = base_image["image"]
                                   image_tasks.append((image_bytes, page_number, img_index))
                   except Exception as e:
                       st.error(LANGUAGES[lang]["error_pdf"].format(error=e))
                       st.stop()

                   def process_image_ocr(image_bytes, page_number, img_index):
                       try:
                           image = Image.open(BytesIO(image_bytes)).convert("RGB")
                           extracted_text = extract_visual_description_with_openai(image)
                       except Exception as e:
                           extracted_text = f"OCR Error on Page {page_number + 1}, Image {img_index + 1} ---\n{e}"
                       return f"\n--- OCR from Page {page_number + 1}, Image {img_index + 1} ---\n{extracted_text}"

                   with st.spinner(LANGUAGES[lang]["processing_images"].format(count=len(image_tasks), time=len(image_tasks) * 2)):
                       max_workers = min(multiprocessing.cpu_count(), len(image_tasks)) or 1
                       with ThreadPoolExecutor(max_workers=max_workers) as executor:
                           ocr_chunks = list(executor.map(lambda args: process_image_ocr(*args), image_tasks))

                       ocr_text = "\n".join(ocr_chunks)
                       combined_text = (pdf_text.strip() + "\n\n" + ocr_text.strip()).strip()

                       st.session_state.aid_storyboard_processed_text = combined_text
                       st.session_state.aid_storyboard_file_name = uploaded_pdf.name
                       st.success(LANGUAGES[lang]["processing_completed"].format(time=time.time() - start_time))
               finally:
                   if os.path.exists(tmpdir):
                       shutil.rmtree(tmpdir, ignore_errors=True)
       else:
           combined_text = st.session_state.aid_storyboard_processed_text

       st.session_state.aid_user_text = combined_text
       st.text_area(LANGUAGES[lang]["extracted_text_ocr"], value=combined_text, height=400)

# ---------------------- SPRACOVANIE VIDEA ----------------------
elif input_type == "TV Commercial (Video 10 - 150 sec)":
   st.markdown(f"### 🎬 {LANGUAGES[lang]['upload_video']}")
   st.markdown(f"###### 🔔 {LANGUAGES[lang]['video_warning']}")

   uploaded_video = st.file_uploader(LANGUAGES[lang]["only upload_video"], type=["mp4", "mov", "mkv", "webm", "flv", "avi"], key="video_uploader")
   youtube_url = st.text_input(LANGUAGES[lang]["video_url"])

   if uploaded_video is not None:
       if not check_file_size(uploaded_video, max_size_mb=200):
           st.stop()
       if "aid_uploaded_video" not in st.session_state or uploaded_video != st.session_state.aid_uploaded_video:
           st.session_state.aid_uploaded_video = uploaded_video
           st.session_state.aid_video_processed = False
           st.session_state.aid_script_created = False

   if youtube_url and not st.session_state.get("aid_uploaded_video") and not st.session_state.get("aid_video_processed", False):
       if not is_valid_url(youtube_url):
           st.error(LANGUAGES[lang]["error_invalid_url"])
           st.stop()
       with tempfile.TemporaryDirectory() as tmpdir:
           try:
               ydl_opts = {
                   'format': 'best[ext=mp4]/best',
                   'merge_output_format': None,
                   'outtmpl': os.path.join(tmpdir, "%(title)s.%(ext)s"),
                   'quiet': True,
               }
               with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                   info_dict = ydl.extract_info(youtube_url, download=True)
                   downloaded_path = ydl.prepare_filename(info_dict)

               with open(downloaded_path, "rb") as video_file:
                   uploaded_bytes = video_file.read()
               video_io = BytesIO(uploaded_bytes)
               video_io.name = os.path.basename(downloaded_path)

               st.session_state.aid_uploaded_video = video_io
               st.session_state.aid_video_processed = False
               st.session_state.aid_script_created = False
               st.success(LANGUAGES[lang]["success_video_download"])
           except Exception as e:
               st.error(LANGUAGES[lang]["error_video_download"].format(error=e))
               st.stop()
           finally:
               if os.path.exists(tmpdir):
                   shutil.rmtree(tmpdir, ignore_errors=True)

   # Spracovanie videa
   if (
       "aid_uploaded_video" in st.session_state and
       st.session_state.aid_uploaded_video and
       not st.session_state.get("aid_video_processed", False) and
       not st.session_state.get("aid_script_created", False)
   ):
       with tempfile.TemporaryDirectory() as tmpdir:
           try:
               uploaded_video = st.session_state.aid_uploaded_video
               video_path = os.path.join(tmpdir, uploaded_video.name)
               with open(video_path, "wb") as f:
                   f.write(uploaded_video.read())

               audio_path = os.path.join(tmpdir, "audio.mp3")
               ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
               subprocess.run([
                   ffmpeg_path, "-i", video_path,
                   "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", audio_path
               ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

               with st.spinner("🎹 Transcribing audio with OpenAI API..."):
                   with open(audio_path, "rb") as audio_file:
                       transcript_response = client.audio.transcriptions.create(
                           model="whisper-1",
                           file=audio_file,
                           prompt = (
    "Toto je scéna, ktorá môže obsahovať hovorený dialóg, spev alebo voice-over. Prosím, presne prepíšte všetok počuteľný text."
    if lang == "sk" else
    "This is a scene that may contain spoken dialogue or sung lyrics or voice over. Please transcribe all audible text accurately."
)
                       )
                       transcript = transcript_response.text.strip()

               with st.spinner("🖼️ Extracting keyframes every 0.5 second using ffmpeg... Please wait..."):
                   frames_dir = os.path.join(tmpdir, "frames")
                   os.makedirs(frames_dir, exist_ok=True)

                   subprocess.run([
                       ffmpeg_path,
                       "-i", video_path,
                       "-vf", "fps=2",
                       os.path.join(frames_dir, "frame_%03d.jpg")
                   ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                   frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
                   total_frames = len(frame_files)
                   if total_frames > 240:
                       st.warning(f"⚠️ Too many frames ({total_frames}). Processing only the first 240.")
                       frame_files = frame_files[:240]
                       total_frames = 240

                   start_time = time.time()
                   progress_bar = st.progress(0)
                   status_placeholder = st.empty()
                   visual_descriptions = [None] * total_frames

                   def process_frame(idx_frame_tuple):
                       idx, frame_file = idx_frame_tuple
                       img_path = os.path.join(frames_dir, frame_file)
                       with open(img_path, "rb") as img_file:
                           encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
                           response = client.chat.completions.create(
                               model="gpt-4o",
                               messages=[
                                   {"role": "user", "content": [
                                       {"type": "text", "text": "Opíš tento záber detailne ako vizuálny scenár alebo storyboard." if lang == "sk" else "Describe this frame in detail like a visual script or storyboard."},
                                       {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                                   ]}
                               ],
                               max_tokens=500
                           )
                           return idx, response.choices[0].message.content.strip()

                   max_workers = min(multiprocessing.cpu_count(), total_frames) or 1
                   with ThreadPoolExecutor(max_workers=max_workers) as executor:
                       for count, result in enumerate(executor.map(process_frame, enumerate(frame_files))):
                           idx, desc = result
                           visual_descriptions[idx] = desc
                           progress_bar.progress((count + 1) / total_frames)
                           if count % 2 == 0:
                               status_placeholder.info(f"🖼️ Processed frame {count + 1} of {total_frames}")

                   st.success(LANGUAGES[lang]["processing_completed"].format(time=time.time() - start_time))

               st.markdown("### 🖼️ Extracted Keyframes")
               cols = st.columns(3)
               col_idx = 0
               for frame_file in frame_files:
                   frame_path = os.path.join(frames_dir, frame_file)
                   if os.path.exists(frame_path):
                       image = Image.open(frame_path)
                       with cols[col_idx % 3]:
                           st.image(image, caption=frame_file, use_container_width=True)
                       col_idx += 1

               full_script = ""
               for idx, desc in enumerate(visual_descriptions):
                   if desc:
                       full_script += f"\nScene {idx + 1}:\n[Visual] {desc}\n"
               full_script += f"\n[Transcripted Audio]\n{transcript}"

               st.session_state.aid_user_text = full_script.strip()
               st.session_state.aid_video_processed = True
               st.success(LANGUAGES[lang]["success_script_created"])
               st.session_state.aid_script_created = True
           finally:
               if os.path.exists(tmpdir):
                   shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------- SPRACOVANIE DRAMATICKÉHO TEXTU ----------------------
elif input_type == "Dramatic Text (TV, Movie, Theatre)":
   st.markdown(f"### 🎭 {LANGUAGES[lang]['paste_dramatic_text']}")
   st.session_state.aid_user_text = st.text_area(LANGUAGES[lang]["paste_dramatic_text"], height=300, key="dramatic_text_input")
   
   uploaded_play = st.file_uploader(LANGUAGES[lang]["upload_dramatic_text"], type=["txt", "docx", "pdf"])
   if uploaded_play is not None:
       if not check_file_size(uploaded_play):
           st.stop()
       if uploaded_play.name.endswith(".txt"):
           text = uploaded_play.read().decode("utf-8")
       elif uploaded_play.name.endswith(".docx"):
           text = docx2txt.process(uploaded_play)
       elif uploaded_play.name.endswith(".pdf"):
           with fitz.open(stream=uploaded_play.read(), filetype="pdf") as doc:
               text = "".join(page.get_text() for page in doc)
       else:
           st.error(LANGUAGES[lang]["error_unsupported_format"])
           text = ""
       st.session_state.aid_user_text = text.strip()

# ---------------------- ZOBRAZENIE A ÚPRAVA SKRIPTU ----------------------
if st.button(LANGUAGES[lang]["show_script"]):
   st.session_state.aid_show_script = True

if st.session_state.get("aid_show_script", False):
   edited_script = st.text_area("Script Text (editable):", value=st.session_state.aid_user_text, height=400, key="script_editor")
   if st.button(LANGUAGES[lang]["save_changes"]):
       st.session_state.aid_user_text = edited_script
       st.success(LANGUAGES[lang]["success_changes_saved"])
       st.text_area("Updated Script:", value=st.session_state.aid_user_text, height=400, key="updated_script")

# ---------------------- SPUSTENIE ANALÝZY ----------------------
if st.button(LANGUAGES[lang]["analyze"]):
    if not st.session_state.aid_user_text.strip():
        st.warning(LANGUAGES[lang]["error_no_content"])
    else:
        with st.spinner("Analyzing, please wait..."):
            result = analyze_text(input_type, st.session_state.aid_user_text)
            st.session_state.aid_analysis_output = result
            st.session_state.aid_chat_history.append({"role": "assistant", "content": result})

            st.markdown(f"### 🔍 {LANGUAGES[lang]['analysis_result']}")

            # Textová plocha
            st.text_area(
                label=LANGUAGES[lang]["analysis_result"],
                value=result,
                height=400,
                key="aid_analysis_text_copyable"
            )

            # JavaScript tlačidlo na kopírovanie do schránky
            components.html(f"""
                <textarea id="copyTarget" style="position:absolute; left:-9999px;">{result}</textarea>
                <button onclick="navigator.clipboard.writeText(document.getElementById('copyTarget').value)">📋 Copy Analysis to Clipboard</button>
            """, height=40)

            # Voliteľné: stiahnutie ako súbor
            st.download_button(
                label="⬇️ Download Analysis as TXT",
                data=result,
                file_name="aid_analysis.txt",
                mime="text/plain"
            )

    # ---------------------- DODATOČNÉ OTÁZKY ----------------------
if st.session_state.aid_analysis_output:
    st.markdown(f"### 🤖 {LANGUAGES[lang]['continue_prompt']}")
    
    # Placeholder pre odpovede
    response_placeholder = st.empty()
    
    # Form s clear_on_submit
    with st.form("followup_form", clear_on_submit=True):
        followup = st.text_area(
            LANGUAGES[lang]["enter_question"],
            height=80,
            placeholder=LANGUAGES[lang]["enter_question"]
        )
        submitted = st.form_submit_button("Send Follow-up Question")
    
    if submitted and followup.strip():
        with st.spinner("🧠 I'm working on the answer..."):
            try:
                # API volanie
                st.session_state.aid_chat_history.append({"role": "user", "content": followup.strip()})
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=st.session_state.aid_chat_history,
                    temperature=0.4,
                    max_tokens=8192
                )
                answer = response.choices[0].message.content
                st.session_state.aid_chat_history.append({"role": "assistant", "content": answer})
                
                # Zobraz v placeholder
                with response_placeholder.container():
                    st.markdown(f"### 💬 {LANGUAGES[lang]['aid_response']}")
    
                     # Otázka
                    st.info(f"**Your question/task:** {followup}")
    
                    # Odpoveď
                    st.markdown("**Answer:**")
                    st.markdown(answer)
    
                    # Tlačidlo na kopírovanie
                    col1, col2, col3 = st.columns([1, 1, 3])
                    with col1:
                        st.download_button(
                            label="📋 Copy Answer",
                            data=answer,
                            file_name="answer.txt",
                            mime="text/plain"
        )
                    
            except Exception as e:
                st.error(f"Error: {e}")

# ---------------------- RESET TLAČIDLÁ ----------------------
col1, col2 = st.columns([1, 5])
with col1:
   if st.button(f"❌ {LANGUAGES[lang]['clear_all']}", key="clear_all_button"):
       st.session_state.clear_all_triggered = True
       st.session_state.aid_image_processing_done = False
       st.session_state.aid_image_processing_key += 1
       st.rerun()

with col2:
   if input_type == "TV Commercial (Video 10 - 150 sec)" and st.button(LANGUAGES[lang]["reset_video"]):
       st.session_state.aid_user_text = ""
       st.session_state.aid_analysis_output = ""
       st.session_state.aid_video_processed = False
       st.session_state.aid_uploaded_video = None
       st.session_state.aid_script_created = False
       st.rerun()