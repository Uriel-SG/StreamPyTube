import streamlit as st
import subprocess
import os
import re
from pathlib import Path
import time
from PIL import Image

# ======================================================
# CONFIGURAZIONE CLOUD (LINUX)
# ======================================================
BASE_DIR = Path(__file__).parent.absolute()

# Invocazione sicura di yt-dlp come modulo Python
YTDLP_CMD = ["python3", "-m", "yt_dlp"]

ICON_PATH = str(BASE_DIR / "pytube_icon.ico")
LOGO_PATH = str(BASE_DIR / "pytube_logo.png")

# Cartella temporanea nel file system del server
TMP_DIR = Path.home() / ".pytube_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Pulizia automatica all'avvio dello script (per gestire lo spazio su Streamlit Cloud)
def clear_tmp_folder():
    for file in TMP_DIR.glob("*"):
        try:
            os.remove(file)
        except:
            pass

# --- CONFIGURAZIONE PAGINA ---
if os.path.exists(ICON_PATH):
    st.set_page_config(page_title="PyTube Web", page_icon=Image.open(ICON_PATH))
else:
    st.set_page_config(page_title="PyTube Web", page_icon="📥")

# --- CSS PER ALLINEAMENTO LOGO-TITOLO ---
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
    clear_tmp_folder() # Pulisce la cartella solo la prima volta che l'utente entra

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
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Template nome file
    output_template = str(TMP_DIR / "%(title)s.%(ext)s")
    
    # COMANDO AGGIORNATO CON FIX ANTIBOT
    cmd = YTDLP_CMD + [
        url,
        "-o", output_template,
        "--newline",
        "--no-check-certificate",
        "--restrict-filenames",
        "--force-overwrites",
        "--no-playlist",
        # Fix per l'errore "Sign in to confirm you're not a bot"
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "--geo-bypass"
    ]

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
            # Debug visibile nei log di Streamlit
            print(f"DEBUG: {line.strip()}")
            
            match = progress_pattern.search(line)
            if match:
                perc = float(match.group(1))
                progress_bar.progress(perc / 100)
                status_text.text(f"Scaricamento in corso: {perc}%")
            
        process.wait()

        if process.returncode == 0:
            # Prendiamo il file più recente creato
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
            st.error("❌ YouTube ha bloccato la richiesta (Bot Detection). Riprova tra poco.")
    except Exception as e:
        st.error(f"Errore critico: {e}")

# ======================================================
# INTERFACCIA UTENTE
# ======================================================
col_logo, col_title = st.columns([0.12, 0.88])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(Image.open(LOGO_PATH), width=55)
with col_title:
    st.title("PyTube Web")

if not st.session_state.download_ready:
    url_input = st.text_input("Inserisci URL YouTube:", placeholder="https://www.youtube.com/watch?v=...")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎵 Scarica MP3"):
            if url_input: process_video(url_input, "mp3")
            else: st.warning("Inserisci un link!")
    with c2:
        if st.button("🎬 Scarica MP4"):
            if url_input: process_video(url_input, "mp4")
            else: st.warning("Inserisci un link!")
else:
    st.balloons()
    st.success(f"File pronto: **{st.session_state.file_name}**")
    
    with open(st.session_state.file_path, "rb") as f:
        st.download_button(
            label="🚀 SCARICA SUL TUO DISPOSITIVO",
            data=f,
            file_name=st.session_state.file_name,
            mime="application/octet-stream"
        )
    
    if st.button("🔄 Converti un altro video"):
        reset_app()

st.divider()
st.caption("PyTube Cloud Service | Ambiente: Streamlit Community Cloud")
