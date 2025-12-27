import streamlit as st
import subprocess
import os
import re
from pathlib import Path
import time
from PIL import Image

# ======================================================
# CONFIGURAZIONE INTELLIGENTE (WINDOWS vs CLOUD/LINUX)
# ======================================================
BASE_DIR = Path(__file__).parent.absolute()

# Rilevamento automatico del sistema operativo
IS_WINDOWS = os.name == 'nt'

if IS_WINDOWS:
    # Percorsi per Windows (usa i file .exe nella cartella)
    YTDLP_EXEC = str(BASE_DIR / "yt-dlp.exe")
    FFMPEG_DIR = str(BASE_DIR)
else:
    # Percorsi per Linux/Streamlit Cloud
    # yt-dlp e ffmpeg vengono richiamati come comandi di sistema
    YTDLP_EXEC = "yt-dlp"
    FFMPEG_DIR = None 

ICON_PATH = str(BASE_DIR / "pytube_icon.ico")
LOGO_PATH = str(BASE_DIR / "pytube_logo.png")

# Cartella temporanea (funziona su entrambi)
TMP_DIR = Path.home() / ".pytube_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# --- CONFIGURAZIONE PAGINA ---
if os.path.exists(ICON_PATH):
    img_icon = Image.open(ICON_PATH)
    st.set_page_config(page_title="PyTube Web", page_icon=img_icon)
else:
    st.set_page_config(page_title="PyTube Web", page_icon="📥")

# --- CSS PER ALLINEAMENTO ---
st.markdown("""
    <style>
    [data-testid="column"] { display: flex; align-items: center; justify-content: flex-start; }
    [data-testid="stHorizontalBlock"] { gap: 0rem; }
    h1 { margin-top: 0px !important; padding-top: 0px !important; padding-left: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'download_ready' not in st.session_state:
    st.session_state.download_ready = False
    st.session_state.file_path = None
    st.session_state.file_name = ""

def reset_app():
    if st.session_state.file_path and os.path.exists(st.session_state.file_path):
        try: os.remove(st.session_state.file_path)
        except: pass
    st.session_state.download_ready = False
    st.session_state.file_path = None
    st.session_state.file_name = ""
    st.rerun()

# ======================================================
# LOGICA DI DOWNLOAD
# ======================================================
def process_video(url, mode):
    # Su Windows controlliamo che l'exe esista davvero
    if IS_WINDOWS and not os.path.exists(YTDLP_EXEC):
        st.error(f"Errore: yt-dlp.exe non trovato in {BASE_DIR}")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()
    output_template = str(TMP_DIR / "%(title)s.%(ext)s")
    
    cmd = [
        YTDLP_EXEC,
        url,
        "-o", output_template,
        "--newline",
        "--no-check-certificate"
    ]

    # Aggiunge la posizione di ffmpeg solo se siamo su Windows
    if IS_WINDOWS:
        cmd += ["--ffmpeg-location", FFMPEG_DIR]

    if mode == "mp3":
        cmd += ["-x", "--audio-format", "mp3"]
    else:
        cmd += ["-f", "mp4"]

    progress_pattern = re.compile(r'(\d{1,3}\.\d)%')

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            text=True, bufsize=1, encoding='utf-8', errors='replace'
        )

        for line in process.stdout:
            match = progress_pattern.search(line)
            if match:
                perc = float(match.group(1))
                progress_bar.progress(perc / 100)
                status_text.text(f"Elaborazione: {perc}%")
            
        process.wait()

        if process.returncode == 0:
            files = sorted(TMP_DIR.glob("*"), key=os.path.getmtime, reverse=True)
            if files:
                st.session_state.file_path = files[0]
                st.session_state.file_name = files[0].name
                st.session_state.download_ready = True
                status_text.success("✅ Conversione completata!")
                progress_bar.empty()
                time.sleep(0.5) 
                st.rerun() 
        else:
            st.error("❌ Errore durante il download.")
    except Exception as e:
        st.error(f"Errore: {e}")

# ======================================================
# INTERFACCIA UTENTE
# ======================================================
col_logo, col_title = st.columns([0.1, 0.9])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(Image.open(LOGO_PATH), width=55)
with col_title:
    st.title("PyTube Web Downloader")

if not st.session_state.download_ready:
    url_input = st.text_input("Incolla l'URL di YouTube:", placeholder="https://...")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎵 Converti in MP3"):
            if url_input: process_video(url_input, "mp3")
            else: st.warning("⚠️ Inserisci un URL.")
    with c2:
        if st.button("🎬 Converti in MP4"):
            if url_input: process_video(url_input, "mp4")
            else: st.warning("⚠️ Inserisci un URL.")
else:
    st.balloons()
    st.success(f"Pronto: **{st.session_state.file_name}**")
    with open(st.session_state.file_path, "rb") as f:
        file_data = f.read()
    st.download_button(
        label="🚀 SCARICA SUL TUO DISPOSITIVO",
        data=file_data,
        file_name=st.session_state.file_name,
        mime="application/octet-stream"
    )
    if st.button("🔄 Converti un altro video"):
        reset_app()

st.divider()
st.caption("Modalità: " + ("Windows (Portable)" if IS_WINDOWS else "Cloud (Linux)"))
