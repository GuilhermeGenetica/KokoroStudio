import customtkinter as ctk
import tkinter.messagebox as msgbox
from tkinter import filedialog 
import os
import sys
import threading
import time
import logging
import re
import numpy as np
import soundfile as sf
import torch
from scipy.io import wavfile
from scipy import signal
import shutil 

# Tentativa de importar pydub para suporte a MP3
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# Tentativa de importar pygame para o Player de Áudio integrado 
try:
    import pygame
    # CORREÇÃO: Forçar a frequência para 24000Hz (padrão do Kokoro) para eliminar o chiado
    pygame.mixer.init(frequency=24000)
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("KokoroStudio")

# --- Configuration & Constants ---
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

# Mapping Languages to Kokoro Codes
LANG_MAP = {
    "🇺🇸 Inglês (Americano)": "a",
    "🇬🇧 Inglês (Britânico)": "b",
    "🇧🇷 Português (Brasil)": "p",
    "🇪🇸 Espanhol": "e",
    "🇫🇷 Francês": "f",
    "🇮🇹 Italiano": "i",
    "🇯🇵 Japonês": "j",
    "🇨🇳 Chinês (Mandarim)": "z",
    "🇮🇳 Hindi": "h"
}

# Mapping Voices (Based on Kokoro v0.19 specs)
# Format: {LangCode: {VoiceName: VoiceID}}
VOICE_MAP = {
    "a": {
        "👩 Bella (Narrativa)": "af_bella", "👩 Sarah (Calma)": "af_sarah", 
        "👩 Nicole (Neutra)": "af_nicole", "👩 Sky (Jovem)": "af_sky",
        "👨 Michael (Neutro)": "am_michael", "👨 Adam (Profundo)": "am_adam",
        "👩 Heart (Suave)": "af_heart", "👨 George (Britânico/US Mix)": "bm_george"
    },
    "b": {
        "👩 Emma (Elegante)": "bf_emma", "👩 Isabella (Clássica)": "bf_isabella",
        "👨 George (Padrão)": "bm_george", "👨 Lewis (Narrador)": "bm_lewis"
    },
    "p": {
        "👨 Alex (Padrão)": "pm_alex", "👩 Dora (Padrão)": "pf_dora",
        "👨 Santa (Temático)": "pm_santa" 
    },
    "e": {"👩 Dora (ES)": "ef_dora", "👨 Alex (ES)": "em_alex", "👨 Santa (ES)": "em_santa"},
    "f": {"👩 Siwis": "ff_siwis"},
    "i": {"👨 Nicola": "im_nicola", "👩 Sara": "if_sara"},
    "j": {"👩 Kokoro (Japonês)": "jf_tebukuro", "👨 Alpha": "jm_kumo"},
    "z": {"👩 Ling": "zf_xiaobei", "👩 Fan": "zf_xiaoni", "👨 Yun": "zm_yunjian"},
    "h": {"👩 Amara": "hf_alpha", "👩 Beta": "hf_beta"}
}

class KokoroStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Kokoro Studio 82M - Pro TTS")
        self.geometry("1300x750") # Aumentado para acomodar o painel lateral
        self.minsize(1000, 600)

        # Variables
        self.pipeline = None
        self.current_lang_code = None
        self.is_generating = False
        self.work_dir = os.getcwd() # Pasta de trabalho padrão
        self.selected_file_path = None # Arquivo selecionado no painel direito
        
        # Variaveis do Player de Audio 
        self.is_playing = False
        self.is_paused = False

        # --- GUI Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0) 
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar (Settings)
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.setup_sidebar()

        # 2. Main Area (Input & Controls)
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.setup_main_area()

        # 3. File Manager Panel (Right Side) - NOVO
        self.file_manager_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.file_manager_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 0))
        self.setup_file_manager()

        # Initialize Default State
        self.update_voice_list("🇺🇸 Inglês (Americano)")
        self.refresh_file_list() # Carrega arquivos iniciais

    def setup_sidebar(self):
        # Header (Ícone limpo)
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="⚙ Configurações", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Language Selection
        self.lang_label = ctk.CTkLabel(self.sidebar_frame, text="Idioma:", anchor="w")
        self.lang_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.lang_option = ctk.CTkOptionMenu(self.sidebar_frame, values=list(LANG_MAP.keys()), command=self.update_voice_list)
        self.lang_option.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Voice Selection
        self.voice_label = ctk.CTkLabel(self.sidebar_frame, text="Voz (Emoção/Timbre):", anchor="w")
        self.voice_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.voice_option = ctk.CTkOptionMenu(self.sidebar_frame, values=[])
        self.voice_option.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        # --- Kokoro Parameters ---
        self.params_label = ctk.CTkLabel(self.sidebar_frame, text="Parâmetros de Síntese", font=ctk.CTkFont(size=16, weight="bold"))
        self.params_label.grid(row=5, column=0, padx=20, pady=(10, 10))

        # Speed
        self.speed_label = ctk.CTkLabel(self.sidebar_frame, text="Velocidade (0.5x - 2.0x):", anchor="w")
        self.speed_label.grid(row=6, column=0, padx=20, pady=(0, 0), sticky="w")
        self.speed_slider = ctk.CTkSlider(self.sidebar_frame, from_=0.5, to=2.0, number_of_steps=15)
        self.speed_slider.set(1.0)
        self.speed_slider.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="ew")
        # Régua de Escala para Velocidade 
        self.create_scale_ruler(self.sidebar_frame, row=8, values=["0.5x", "1.0x", "1.5x", "2.0x"])

        # --- Post Processing ---
        self.dsp_label = ctk.CTkLabel(self.sidebar_frame, text="Efeitos (Pós-Processamento)", font=ctk.CTkFont(size=16, weight="bold"))
        self.dsp_label.grid(row=9, column=0, padx=20, pady=(10, 10))

        # Volume Gain
        self.vol_label = ctk.CTkLabel(self.sidebar_frame, text="Volume (Ganho dB):", anchor="w")
        self.vol_label.grid(row=10, column=0, padx=20, pady=(0, 0), sticky="w")
        self.vol_slider = ctk.CTkSlider(self.sidebar_frame, from_=-10, to=10, number_of_steps=20)
        self.vol_slider.set(0)
        self.vol_slider.grid(row=11, column=0, padx=20, pady=(0, 5), sticky="ew")
        # Régua de Escala para Volume 
        self.create_scale_ruler(self.sidebar_frame, row=12, values=["-10dB", "0dB", "+10dB"])

        # Pitch Shift (Simulated)
        self.pitch_label = ctk.CTkLabel(self.sidebar_frame, text="Pitch (Tom):", anchor="w")
        self.pitch_label.grid(row=13, column=0, padx=20, pady=(0, 0), sticky="w")
        self.pitch_slider = ctk.CTkSlider(self.sidebar_frame, from_=0.8, to=1.2, number_of_steps=20)
        self.pitch_slider.set(1.0)
        self.pitch_slider.grid(row=14, column=0, padx=20, pady=(0, 5), sticky="ew")
        # Régua de Escala para Pitch 
        self.create_scale_ruler(self.sidebar_frame, row=15, values=["Grave", "Normal", "Agudo"])
        
        # Info Box
        self.info_box = ctk.CTkTextbox(self.sidebar_frame, height=100, text_color="gray")
        self.info_box.grid(row=16, column=0, padx=20, pady=20, sticky="ew")
        self.info_box.insert("0.0", "Info: 'Emoção' no Kokoro é definida pela escolha da Voz. Use os controles deslizantes para refinar o resultado.")
        self.info_box.configure(state="disabled")

    def create_scale_ruler(self, parent, row, values):
        """Cria uma régua visual simples abaixo dos sliders."""
        ruler_frame = ctk.CTkFrame(parent, fg_color="transparent", height=15)
        ruler_frame.grid(row=row, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Distribui os labels
        for i, val in enumerate(values):
            lbl = ctk.CTkLabel(ruler_frame, text=val, font=ctk.CTkFont(size=10), text_color="gray")
            if i == 0:
                lbl.pack(side="left")
            elif i == len(values) - 1:
                lbl.pack(side="right")
            else:
                # Tenta centralizar elementos do meio (aproximado)
                lbl.pack(side="left", padx=15, expand=True)

    def setup_main_area(self):
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Title
        self.main_label = ctk.CTkLabel(self.main_frame, text="Texto para Fala (TTS Input)", font=ctk.CTkFont(size=24, weight="bold"))
        self.main_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nw")

        # Text Input
        self.text_input = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(size=16))
        self.text_input.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.text_input.insert("0.0", "The sky above the port was the color of television, tuned to a dead channel.")

        # Control Bar (Filename & Play)
        self.control_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.control_bar.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        self.control_bar.grid_columnconfigure(1, weight=1)

        # File Label
        self.file_label = ctk.CTkLabel(self.control_bar, text="Nome do Ficheiro:", font=ctk.CTkFont(weight="bold"))
        self.file_label.grid(row=0, column=0, padx=(0, 10))

        # File Entry
        self.filename_entry = ctk.CTkEntry(self.control_bar, placeholder_text="audio_kokoro (vazio para automático)")
        self.filename_entry.grid(row=0, column=1, sticky="ew", padx=(0, 20))

        # Extension Label -> Agora Format Selection 
        # Substituindo label estático por OptionMenu
        self.format_var = ctk.StringVar(value=".mp3")
        self.format_menu = ctk.CTkOptionMenu(self.control_bar, values=[".mp3", ".wav"], 
                                             variable=self.format_var, width=80)
        self.format_menu.grid(row=0, column=2, padx=(0, 20))

        # Generate Button (Ícone ajustado para visual limpo)
        self.generate_btn = ctk.CTkButton(self.control_bar, text="► PLAY / GERAR", height=50, 
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          fg_color="green", hover_color="darkgreen",
                                          command=self.start_generation_thread)
        self.generate_btn.grid(row=0, column=3, padx=0)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_bar.set(0)

        # Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="Pronto.", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

    def setup_file_manager(self):
        """Configura o painel direito de gerenciamento de arquivos."""
        self.file_manager_frame.grid_rowconfigure(3, weight=1) # Atualizado weight para a linha 3 (lista)
        self.file_manager_frame.grid_columnconfigure(0, weight=1)

        # Título
        lbl_title = ctk.CTkLabel(self.file_manager_frame, text="🗀 Gestor de Ficheiros", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_title.grid(row=0, column=0, padx=10, pady=(20, 10), sticky="w")

        # Seleção de Pasta
        self.folder_btn = ctk.CTkButton(self.file_manager_frame, text="Selecionar Pasta", command=self.select_work_folder)
        self.folder_btn.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # --- NOVA CAIXA DE TEXTO (Endereço Completo) ---
        self.folder_path_entry = ctk.CTkEntry(self.file_manager_frame, text_color="gray", font=ctk.CTkFont(size=11))
        self.folder_path_entry.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.folder_path_entry.insert(0, self.work_dir)
        self.folder_path_entry.configure(state="readonly")

        # Lista de Arquivos (Scrollable) - Movido para Row 3
        self.file_list_frame = ctk.CTkScrollableFrame(self.file_manager_frame, label_text="Ficheiros de Áudio")
        self.file_list_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        # Botões de Ação - Movido para Row 4 (Ícones substituídos por Unicode limpo)
        action_frame = ctk.CTkFrame(self.file_manager_frame, fg_color="transparent")
        action_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        action_frame.columnconfigure((0,1,2), weight=1)

        self.btn_rename = ctk.CTkButton(action_frame, text="✎", font=ctk.CTkFont(size=16), width=30, command=self.action_rename_file, state="disabled")
        self.btn_rename.grid(row=0, column=0, padx=2, sticky="ew")
        
        self.btn_convert = ctk.CTkButton(action_frame, text="MP3", font=ctk.CTkFont(size=12, weight="bold"), width=30, command=self.action_convert_mp3, state="disabled")
        self.btn_convert.grid(row=0, column=1, padx=2, sticky="ew")

        self.btn_delete = ctk.CTkButton(action_frame, text="✖", font=ctk.CTkFont(size=14), width=30, fg_color="red", hover_color="darkred", command=self.action_delete_file, state="disabled")
        self.btn_delete.grid(row=0, column=2, padx=2, sticky="ew")

        # --- NOVO PAINEL DE PLAYER DE ÁUDIO --- Movido para Row 5
        self.player_frame = ctk.CTkFrame(self.file_manager_frame, fg_color="transparent")
        self.player_frame.grid(row=5, column=0, padx=10, pady=(0, 20), sticky="ew")
        
        # Barra de progresso do áudio
        self.audio_progress = ctk.CTkProgressBar(self.player_frame)
        self.audio_progress.pack(fill="x", pady=(0, 10))
        self.audio_progress.set(0)

        # Container dos botões do Player (Ícones substituídos por caracteres de media padrão)
        player_btns = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        player_btns.pack(fill="x")
        player_btns.columnconfigure((0,1,2,3,4), weight=1)

        self.btn_rev = ctk.CTkButton(player_btns, text="<<", font=ctk.CTkFont(size=14, weight="bold"), width=30, command=self.audio_reverse, state="disabled")
        self.btn_rev.grid(row=0, column=0, padx=2, sticky="ew")
        
        self.btn_play = ctk.CTkButton(player_btns, text="►", font=ctk.CTkFont(size=16), width=30, command=self.audio_play, state="disabled")
        self.btn_play.grid(row=0, column=1, padx=2, sticky="ew")
        
        self.btn_pause = ctk.CTkButton(player_btns, text="❚❚", font=ctk.CTkFont(size=12, weight="bold"), width=30, command=self.audio_pause, state="disabled")
        self.btn_pause.grid(row=0, column=2, padx=2, sticky="ew")
        
        self.btn_stop = ctk.CTkButton(player_btns, text="■", font=ctk.CTkFont(size=16), width=30, command=self.audio_stop, state="disabled")
        self.btn_stop.grid(row=0, column=3, padx=2, sticky="ew")
        
        self.btn_fwd = ctk.CTkButton(player_btns, text=">>", font=ctk.CTkFont(size=14, weight="bold"), width=30, command=self.audio_forward, state="disabled")
        self.btn_fwd.grid(row=0, column=4, padx=2, sticky="ew")

    # --- LÓGICA DO PLAYER DE ÁUDIO  ---
    def audio_play(self):
        if not HAS_PYGAME:
            msgbox.showwarning("Aviso", "A biblioteca 'pygame' não está instalada.\nPara o painel de áudio funcionar, instale com o comando:\npip install pygame")
            return
        if not self.selected_file_path or not os.path.exists(self.selected_file_path): 
            return
        
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
        else:
            try:
                pygame.mixer.music.load(self.selected_file_path)
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                # Inicia rastreio da barra de progresso numa Thread para não travar a UI
                threading.Thread(target=self.track_audio_progress, daemon=True).start()
            except Exception as e:
                msgbox.showerror("Erro de Reprodução", f"Não foi possível reproduzir o áudio:\n{str(e)}")
                return
                
        self.update_player_buttons()

    def audio_pause(self):
        if HAS_PYGAME and self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            self.update_player_buttons()

    def audio_stop(self):
        if HAS_PYGAME:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.audio_progress.set(0)
            self.update_player_buttons()

    def audio_forward(self):
        if HAS_PYGAME and self.is_playing:
            try:
                current_pos = pygame.mixer.music.get_pos() / 1000.0
                pygame.mixer.music.set_pos(current_pos + 5.0)
            except Exception as e:
                logger.warning(f"Avançar não suportado neste formato/sistema: {e}")

    def audio_reverse(self):
        if HAS_PYGAME and self.is_playing:
            try:
                current_pos = pygame.mixer.music.get_pos() / 1000.0
                new_pos = max(0.0, current_pos - 5.0)
                pygame.mixer.music.rewind()
                pygame.mixer.music.set_pos(new_pos)
            except Exception as e:
                logger.warning(f"Retroceder não suportado neste formato/sistema: {e}")

    def track_audio_progress(self):
        if not HAS_PYGAME: return
        
        try:
            # Obtém a duração total do ficheiro
            if HAS_PYDUB and self.selected_file_path:
                audio = AudioSegment.from_file(self.selected_file_path)
                duration = audio.duration_seconds
            else:
                duration = pygame.mixer.Sound(self.selected_file_path).get_length()
        except:
            duration = 100 # Prevenção de erro
            
        if duration <= 0: return

        while self.is_playing or self.is_paused:
            if self.is_playing and pygame.mixer.music.get_busy():
                current_pos = pygame.mixer.music.get_pos() / 1000.0
                progress = min(1.0, current_pos / duration)
                self.audio_progress.set(progress)
            elif self.is_playing and not pygame.mixer.music.get_busy():
                # Ficheiro chegou ao fim
                self.is_playing = False
                self.audio_progress.set(1.0)
                self.after(0, self.update_player_buttons)
                break
            time.sleep(0.1) # Atualiza a barra a cada 100ms

    def update_player_buttons(self):
        # Atualiza o estado dos botões visualmente
        if self.is_playing:
            self.btn_play.configure(state="disabled")
            self.btn_pause.configure(state="normal")
            self.btn_stop.configure(state="normal")
            self.btn_fwd.configure(state="normal")
            self.btn_rev.configure(state="normal")
        elif self.is_paused:
            self.btn_play.configure(state="normal")
            self.btn_pause.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.btn_fwd.configure(state="disabled")
            self.btn_rev.configure(state="disabled")
        else: # Parado
            if self.selected_file_path:
                self.btn_play.configure(state="normal")
            self.btn_pause.configure(state="disabled")
            self.btn_stop.configure(state="disabled")
            self.btn_fwd.configure(state="disabled")
            self.btn_rev.configure(state="disabled")
            self.audio_progress.set(0)

    # --- FUNÇÕES ORIGINAIS MODIFICADAS PARA INCLUIR ATUALIZAÇÃO DO PLAYER ---

    def select_work_folder(self):
        folder = filedialog.askdirectory(initialdir=self.work_dir)
        if folder:
            self.work_dir = folder
            
            # Atualizar a nova caixa de texto completa
            self.folder_path_entry.configure(state="normal")
            self.folder_path_entry.delete(0, "end")
            self.folder_path_entry.insert(0, self.work_dir)
            self.folder_path_entry.configure(state="readonly")
            
            self.refresh_file_list()
            self.audio_stop() # Parar áudio anterior se houver

    def refresh_file_list(self):
        """Atualiza a lista visual de arquivos na pasta de trabalho."""
        # Limpar lista atual
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        try:
            files = [f for f in os.listdir(self.work_dir) if f.lower().endswith(('.wav', '.mp3'))]
            files.sort()
            
            self.file_widgets = {} # Mapeia nome -> botão

            for f in files:
                btn = ctk.CTkButton(self.file_list_frame, text=f, anchor="w", fg_color="transparent", border_width=1, border_color="#333",
                                    command=lambda name=f: self.on_file_select(name))
                btn.pack(fill="x", pady=2)
                self.file_widgets[f] = btn
        except Exception as e:
            logger.error(f"Error listing files: {e}")

    def on_file_select(self, filename):
        # Resetar visual
        for btn in self.file_widgets.values():
            btn.configure(fg_color="transparent")
        
        # Destacar selecionado
        if filename in self.file_widgets:
            self.file_widgets[filename].configure(fg_color="#3B8ED0")
        
        self.selected_file_path = os.path.join(self.work_dir, filename)
        
        # Habilitar botões
        self.btn_rename.configure(state="normal")
        self.btn_delete.configure(state="normal")
        self.btn_convert.configure(state="normal")
        
        # Atualização do Player
        self.audio_stop()
        self.btn_play.configure(state="normal")

    def action_rename_file(self):
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            return
        
        current_name = os.path.basename(self.selected_file_path)
        new_name = ctk.CTkInputDialog(text="Novo nome (com extensão):", title="Renomear").get_input()
        
        if new_name:
            new_path = os.path.join(self.work_dir, new_name)
            try:
                self.audio_stop() # Parar o player antes de renomear o ficheiro
                os.rename(self.selected_file_path, new_path)
                self.refresh_file_list()
                self.status_label.configure(text=f"Renomeado para {new_name}")
            except Exception as e:
                msgbox.showerror("Erro", str(e))

    def action_delete_file(self):
        if not self.selected_file_path:
            return
        if msgbox.askyesno("Confirmar", "Tem certeza que deseja apagar este arquivo?"):
            try:
                self.audio_stop() # Parar o player antes de apagar
                os.remove(self.selected_file_path)
                self.refresh_file_list()
                self.selected_file_path = None
                self.btn_rename.configure(state="disabled")
                self.btn_delete.configure(state="disabled")
                self.btn_convert.configure(state="disabled")
                self.btn_play.configure(state="disabled") # Desativar Play
            except Exception as e:
                msgbox.showerror("Erro", str(e))

    def action_convert_mp3(self):
        if not self.selected_file_path:
            return
        
        if not HAS_PYDUB:
            msgbox.showwarning("Aviso", "Biblioteca 'pydub' não encontrada. Instale com 'pip install pydub' e certifique-se de ter o ffmpeg instalado.")
            return

        target_file = self.selected_file_path
        if target_file.lower().endswith(".mp3"):
            msgbox.showinfo("Info", "O arquivo já é MP3.")
            return

        try:
            self.status_label.configure(text="Convertendo para MP3...")
            audio = AudioSegment.from_file(target_file)
            new_filename = os.path.splitext(target_file)[0] + ".mp3"
            audio.export(new_filename, format="mp3")
            self.refresh_file_list()
            self.status_label.configure(text=f"Convertido: {os.path.basename(new_filename)}")
        except Exception as e:
            msgbox.showerror("Erro na Conversão", f"Certifique-se que o ffmpeg está instalado.\n{str(e)}")

    def update_voice_list(self, choice):
        """Updates the voice dropdown based on selected language."""
        lang_code = LANG_MAP[choice]
        voices = VOICE_MAP.get(lang_code, {})
        self.voice_option.configure(values=list(voices.keys()))
        if voices:
            self.voice_option.set(list(voices.keys())[0])
        else:
            self.voice_option.set("Padrão")

    def get_auto_filename(self, extension=".wav"):
        """Generates audio_kokoro_X.ext filename."""
        base_name = "audio_kokoro"
        counter = 1
        while True:
            filename = f"{base_name}_{counter}{extension}"
            full_path = os.path.join(self.work_dir, filename)
            if not os.path.exists(full_path):
                return full_path
            counter += 1

    def start_generation_thread(self):
        """Starts generation in a separate thread to keep UI responsive."""
        if self.is_generating:
            return
        
        # UI Validation
        text = self.text_input.get("0.0", "end").strip()
        if not text:
            msgbox.showwarning("Aviso", "Por favor, insira algum texto.")
            return

        # Filename Logic
        user_name = self.filename_entry.get().strip()
        selected_format = self.format_var.get() # .mp3 ou .wav

        if not user_name:
            # Auto filename com caminho completo da pasta de trabalho
            filepath = self.get_auto_filename(selected_format)
        else:
            # Sanitize filename
            user_name = re.sub(r'[\\/*?:"<>|]', "", user_name)
            if not user_name.lower().endswith(selected_format):
                user_name += selected_format
            filepath = os.path.join(self.work_dir, user_name)
            
            if os.path.exists(filepath):
                if not msgbox.askyesno("Sobrescrever?", f"O arquivo '{os.path.basename(filepath)}' já existe. Deseja sobrescrever?"):
                    return

        # Lock UI
        self.is_generating = True
        self.generate_btn.configure(state="disabled", text="Gerando...")
        self.progress_bar.start()
        
        # Thread
        threading.Thread(target=self.generate_audio_process, args=(text, filepath, selected_format), daemon=True).start()

    def generate_audio_process(self, text, filepath, file_format):
        """Core logic for TTS generation and processing."""
        try:
            from kokoro import KPipeline
            
            # 1. Get Settings
            selected_lang_name = self.lang_option.get()
            lang_code = LANG_MAP[selected_lang_name]
            
            selected_voice_name = self.voice_option.get()
            voice_code = VOICE_MAP[lang_code][selected_voice_name]
            
            speed = self.speed_slider.get()
            volume_gain = self.vol_slider.get()
            pitch_shift = self.pitch_slider.get()

            self.update_status("Carregando Pipeline Kokoro...")
            logger.info(f"Loading Pipeline: {lang_code}, Voice: {voice_code}")

            # 2. Initialize Pipeline (Lazy Loading)
            # Re-initialize only if lang changed or first run
            if self.pipeline is None or self.current_lang_code != lang_code:
                 # Force CPU for stability on generic hardware
                self.pipeline = KPipeline(lang_code=lang_code, device='cpu')
                self.current_lang_code = lang_code

            self.update_status("Sintetizando áudio...")
            
            # 3. Generate Audio
            generator = self.pipeline(text, voice=voice_code, speed=speed, split_pattern=r'\n+')
            
            audio_segments = []
            for i, (gs, ps, audio) in enumerate(generator):
                if audio is not None:
                    audio_segments.append(audio)
            
            if not audio_segments:
                raise Exception("Nenhum áudio foi gerado pelo modelo.")

            # Concatenate
            full_audio = np.concatenate(audio_segments)

            # 4. Post-Processing (Effects)
            self.update_status("Aplicando efeitos...")
            
            # Apply Pitch Shift (Resampling method)
            if pitch_shift != 1.0:
                # Resampling changes speed too, so we compensate speed if needed, 
                # but simple resampling is often what users perceive as pitch shift in simple tools.
                new_len = int(len(full_audio) / pitch_shift)
                full_audio = signal.resample(full_audio, new_len)

            # Apply Volume Gain
            if volume_gain != 0:
                # DB to linear conversion: 10^(db/20)
                gain_factor = 10 ** (volume_gain / 20)
                full_audio = full_audio * gain_factor

            # Clipping protection
            max_val = np.max(np.abs(full_audio))
            if max_val > 1.0:
                full_audio = full_audio / max_val
                logger.warning("Audio normalized to prevent clipping.")

            # 5. Save File
            self.update_status(f"Salvando {os.path.basename(filepath)}...")
            
            # Se for MP3, primeiro salvamos como WAV temporário, depois convertemos com pydub
            if file_format == ".mp3":
                if not HAS_PYDUB:
                    # Fallback se não tiver pydub: Salva como wav e avisa
                    filepath = filepath.replace(".mp3", ".wav")
                    sf.write(filepath, full_audio, 24000)
                    raise Exception("PyDub não instalado. Salvo como .wav.")
                else:
                    # Salva WAV temp na memória ou disco
                    temp_wav = filepath.replace(".mp3", "_temp.wav")
                    sf.write(temp_wav, full_audio, 24000)
                    
                    # Converte
                    audio_seg = AudioSegment.from_wav(temp_wav)
                    audio_seg.export(filepath, format="mp3")
                    
                    # Remove temp
                    if os.path.exists(temp_wav):
                        os.remove(temp_wav)
            else:
                # Salvar WAV direto
                sf.write(filepath, full_audio, 24000)
            
            # Atualiza lista de arquivos no final
            self.after(0, self.refresh_file_list)
            
            self.finish_generation(True, f"Sucesso! Salvo: {os.path.basename(filepath)}")
            logger.info(f"Generated: {filepath}")

        except Exception as e:
            logger.error(f"Generation Failed: {e}", exc_info=True)
            self.finish_generation(False, str(e))

    def update_status(self, message):
        self.status_label.configure(text=message)

    def finish_generation(self, success, message):
        self.is_generating = False
        self.progress_bar.stop()
        self.progress_bar.set(1 if success else 0)
        self.generate_btn.configure(state="normal", text="► PLAY / GERAR")
        self.status_label.configure(text=message, text_color="green" if success else "red")
        
        if not success:
            msgbox.showerror("Erro de Geração", message)

if __name__ == "__main__":
    # Ensure working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    app = KokoroStudioApp()
    app.mainloop()

    # Criado por GMO.