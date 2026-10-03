"""YouTube Metadata Translator — desktop GUI (customtkinter, Windows/macOS/Linux)."""
import os
import queue
import shutil
import threading
import tkinter.filedialog as filedialog
from datetime import datetime

import customtkinter as ctk

import yt_metadata_translator as eng

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT = ("Segoe UI", 14)
FONT_SMALL = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 15, "bold")
LANG_CODES = ("en", "uk", "ru")

GUI_STRINGS = {
    "en": {
        "app_title": "YouTube Metadata Translator",
        "lang_name": "English",
        "tab_translate": "Translate", "tab_playlists": "Playlists",
        "tab_schedule": "Publishing", "tab_settings": "Settings", "tab_profile": "Profile",
        "choose_language": "Interface language", "your_name": "Your name",
        "next": "Next", "save": "Save", "back": "Back",
        "secrets_missing": "No client_secrets file found. Pick the JSON downloaded from Google Cloud.",
        "secrets_pick": "Pick client_secrets.json",
        "profile_title": "Channels", "profile_name": "New channel profile name",
        "profile_add": "Add channel (pick client_secrets.json)", "profile_continue": "Continue",
        "auth_opening": "Browser will open — sign in to the channel's Google account…",
        "auth_ok": "Authorized: {channel}", "auth_failed": "Authorization failed: {error}",
        "tr_mode": "What to translate", "tr_last": "Latest video", "tr_specific": "Specific videos",
        "tr_all": "All videos", "tr_type": "Video type", "tr_long": "Long", "tr_short": "Short",
        "tr_links": "Video links (one per line)", "tr_source": "Title and description",
        "tr_source_video": "From the video", "tr_source_manual": "Enter manually",
        "tr_manual_title": "Custom title (empty — keep the video's one)",
        "tr_manual_desc": "Custom description (empty — keep the video's one)",
        "tr_parts": "What to localize", "parts_all": "Everything", "parts_titles": "Titles only",
        "parts_descs": "Descriptions only", "tr_start": "Translate and apply",
        "tr_done_all": "✓ Done", "tr_no_matches": "No matching videos found.",
        "tr_found": "Found {n} video(s)", "tr_pick_model": "Pick a model",
        "pl_defaults": "Default playlists (new videos go here)",
        "pl_name": "Playlist name", "pl_id": "Playlist link or ID",
        "pl_add_playlist": "Add playlist", "pl_add_video": "Add a video to playlists",
        "pl_video_link": "Video link or ID", "pl_added": "Added to {n} playlist(s)",
        "pl_target_pick": "Pick playlists (multiple allowed)",
        "sched_link": "Video link or ID", "sched_date": "Publishing date (ddmmyy)",
        "sched_set": "Schedule", "sched_done": "✓ Scheduled for {date}", "sched_bad_date": "Invalid date",
        "set_interface": "Interface", "set_language": "Language", "set_name": "Your name",
        "set_parallel": "Parallel translations", "set_auto": "Auto",
        "set_ask_playlists": "Ask about playlists after translation",
        "set_ask_schedule": "Ask about deferred publishing after translation",
        "set_saved": "✓ Saved",
        "api_title": "API providers", "api_activate": "Make active",
        "api_online": "Online", "api_local": "Local", "api_keys_n": "{n} key(s)",
    },
    "uk": {
        "app_title": "YouTube Metadata Translator",
        "lang_name": "Українська",
        "tab_translate": "Переклад", "tab_playlists": "Плейлисти",
        "tab_schedule": "Публікація", "tab_settings": "Налаштування", "tab_profile": "Профіль",
        "choose_language": "Мова інтерфейсу", "your_name": "Ваше ім'я",
        "next": "Далі", "save": "Зберегти", "back": "Назад",
        "secrets_missing": "Не знайдено client_secrets. Виберіть JSON, завантажений з Google Cloud.",
        "secrets_pick": "Виберіть client_secrets.json",
        "profile_title": "Канали", "profile_name": "Назва нового профілю каналу",
        "profile_add": "Додати канал (виберіть client_secrets.json)", "profile_continue": "Продовжити",
        "auth_opening": "Відкриється браузер — увійдіть в Google-акаунт каналу…",
        "auth_ok": "Авторизовано: {channel}", "auth_failed": "Помилка авторизації: {error}",
        "tr_mode": "Що перекладаємо", "tr_last": "Останнє відео", "tr_specific": "Конкретні відео",
        "tr_all": "Усі відео", "tr_type": "Тип відео", "tr_long": "Лонг", "tr_short": "Шортс",
        "tr_links": "Посилання на відео (по одному в рядку)", "tr_source": "Назва та опис",
        "tr_source_video": "З відео", "tr_source_manual": "Вписати самому",
        "tr_manual_title": "Своя назва (порожньо — залишити з відео)",
        "tr_manual_desc": "Свій опис (порожньо — залишити з відео)",
        "tr_parts": "Що локалізуємо", "parts_all": "Усе", "parts_titles": "Тільки назви",
        "parts_descs": "Тільки описи", "tr_start": "Перекласти та застосувати",
        "tr_done_all": "✓ Готово", "tr_no_matches": "Підходящих відео не знайдено.",
        "tr_found": "Знайдено {n} відео", "tr_pick_model": "Виберіть модель",
        "pl_defaults": "Плейлисти за замовчуванням (нові відео попадатимуть сюди)",
        "pl_name": "Назва плейлиста", "pl_id": "Посилання на плейлист або ID",
        "pl_add_playlist": "Додати плейлист", "pl_add_video": "Додати відео до плейлистів",
        "pl_video_link": "Посилання на відео або ID", "pl_added": "Додано до {n} плейлистів",
        "pl_target_pick": "Вибрати плейлисти (можна кілька)",
        "sched_link": "Посилання на відео або ID", "sched_date": "Дата публікації (ddmmyy)",
        "sched_set": "Запланувати", "sched_done": "✓ Заплановано на {date}", "sched_bad_date": "Некоректна дата",
        "set_interface": "Інтерфейс", "set_language": "Мова", "set_name": "Ваше ім'я",
        "set_parallel": "Одночасні переклади", "set_auto": "Авто",
        "set_ask_playlists": "Питати про плейлисти після перекладу",
        "set_ask_schedule": "Питати про відкладену публікацію після перекладу",
        "set_saved": "✓ Збережено",
        "api_title": "API-провайдери", "api_activate": "Зробити активним",
        "api_online": "Онлайн", "api_local": "Локальний", "api_keys_n": "ключів: {n}",
    },
    "ru": {
        "app_title": "YouTube Metadata Translator",
        "lang_name": "Русский",
        "tab_translate": "Перевод", "tab_playlists": "Плейлисты",
        "tab_schedule": "Публикация", "tab_settings": "Настройки", "tab_profile": "Профиль",
        "choose_language": "Язык интерфейса", "your_name": "Твоё имя",
        "next": "Далее", "save": "Сохранить", "back": "Назад",
        "secrets_missing": "Не найден client_secrets. Выбери JSON, скачанный из Google Cloud.",
        "secrets_pick": "Выбери client_secrets.json",
        "profile_title": "Каналы", "profile_name": "Название нового профиля канала",
        "profile_add": "Добавить канал (выбери client_secrets.json)", "profile_continue": "Продолжить",
        "auth_opening": "Откроется браузер — войди в Google-аккаунт канала…",
        "auth_ok": "Авторизовано: {channel}", "auth_failed": "Ошибка авторизации: {error}",
        "tr_mode": "Что переводим", "tr_last": "Последнее видео", "tr_specific": "Конкретные видео",
        "tr_all": "Все видео", "tr_type": "Тип видео", "tr_long": "Лонг", "tr_short": "Шортс",
        "tr_links": "Ссылки на видео (по одной в строке)", "tr_source": "Название и описание",
        "tr_source_video": "Из видео", "tr_source_manual": "Вписать самому",
        "tr_manual_title": "Своё название (пусто — оставить с видео)",
        "tr_manual_desc": "Своё описание (пусто — оставить с видео)",
        "tr_parts": "Что локализуем", "parts_all": "Всё", "parts_titles": "Только названия",
        "parts_descs": "Только описания", "tr_start": "Перевести и применить",
        "tr_done_all": "✓ Готово", "tr_no_matches": "Подходящих видео не найдено.",
        "tr_found": "Найдено {n} видео", "tr_pick_model": "Выбери модель",
        "pl_defaults": "Плейлисты по умолчанию (новые видео будут попадать сюда)",
        "pl_name": "Название плейлиста", "pl_id": "Ссылка на плейлист или ID",
        "pl_add_playlist": "Добавить плейлист", "pl_add_video": "Добавить видео в плейлисты",
        "pl_video_link": "Ссылка на видео или ID", "pl_added": "Добавлено в {n} плейлистов",
        "pl_target_pick": "Выбрать плейлисты (можно несколько)",
        "sched_link": "Ссылка на видео или ID", "sched_date": "Дата публикации (ddmmyy)",
        "sched_set": "Запланировать", "sched_done": "✓ Запланировано на {date}", "sched_bad_date": "Некорректная дата",
        "set_interface": "Интерфейс", "set_language": "Язык", "set_name": "Твоё имя",
        "set_parallel": "Одновременные переводы", "set_auto": "Авто",
        "set_ask_playlists": "Спрашивать про плейлисты после перевода",
        "set_ask_schedule": "Спрашивать про отложенную публикацию после перевода",
        "set_saved": "✓ Сохранено",
        "api_title": "API-провайдеры", "api_activate": "Сделать активным",
        "api_online": "Онлайн", "api_local": "Локальный", "api_keys_n": "ключей: {n}",
    },
}


def g(key, **kwargs):
    lang = eng._ui.get("language") or "en"
    text = GUI_STRINGS.get(lang, GUI_STRINGS["en"]).get(key) or GUI_STRINGS["en"][key]
    return text.format(**kwargs) if kwargs else text


def create_profile_gui(name, secrets_path):
    """Profile creation without console prompts (GUI variant of the wizard)."""
    profiles = eng.load_channel_profiles()
    secrets_name = os.path.basename(secrets_path)
    dest = eng.data_file_path(
        secrets_name if secrets_name.startswith("client_secrets") else "client_secrets.json")
    if not os.path.exists(dest):
        shutil.copy(secrets_path, dest)
    profile_id = eng.profile_slug(name, {p["profile_id"] for p in profiles["profiles"]})
    profile = {
        "profile_id": profile_id,
        "display_name": name,
        "channel_id": "",
        "channel_title": "",
        "token_file": f"profiles/{profile_id}/token.pickle",
        "client_secrets_file": os.path.basename(dest),
        "playlists": [],
        "default_playlists": [],
        "languages": [],
        "publ_calendar_file": f"profiles/{profile_id}/calendar.json",
    }
    profiles["profiles"].append(profile)
    eng.save_channel_profiles(profiles)
    eng.save_json_file(profile["publ_calendar_file"], {})
    return profile


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(g("app_title"))
        self.geometry("1080x720")
        self.minsize(960, 640)
        self.profile = None
        self.youtube = None
        self.log_box = None
        self.lang_labels = {}
        self.show_onboarding()

    # ---------- helpers ----------

    def log(self, text):
        """Thread-safe append to the on-screen log."""
        def append():
            if self.log_box and self.log_box.winfo_exists():
                self.log_box.configure(state="normal")
                self.log_box.insert("end", text + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        self.after(0, append)

    def lang_status(self, code, state, detail=""):
        colors = {"ok": "#4ade80", "fail": "#f87171", "retry": "#fbbf24", "start": "#93c5fd"}
        def update():
            label = self.lang_labels.get(code)
            if label and label.winfo_exists():
                label.configure(text=f"{code}: {state} {detail}".strip(),
                                text_color=colors.get(state))
        self.after(0, update)

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    # ---------- onboarding ----------

    def show_onboarding(self):
        self.clear()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both")
        ctk.CTkLabel(frame, text=g("app_title"), font=("Segoe UI", 26, "bold")).pack(pady=(90, 40))
        ctk.CTkLabel(frame, text=g("choose_language"), font=FONT).pack(pady=(0, 6))
        names = [GUI_STRINGS[c]["lang_name"] for c in LANG_CODES]
        codes = {GUI_STRINGS[c]["lang_name"]: c for c in LANG_CODES}
        lang_menu = ctk.CTkOptionMenu(frame, values=names, font=FONT,
                                      command=lambda v: (self.switch_language(codes[v]),
                                                         self.show_onboarding()))
        lang_menu.set(GUI_STRINGS[eng._ui.get("language") or "en"]["lang_name"])
        lang_menu.pack()
        ctk.CTkLabel(frame, text=g("your_name"), font=FONT).pack(pady=(28, 6))
        name_entry = ctk.CTkEntry(frame, width=320, font=FONT)
        name_entry.pack()
        status = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color="#fbbf24")
        status.pack(pady=10)

        def proceed():
            name = name_entry.get().strip()
            if not name:
                status.configure(text=g("your_name"))
                return
            eng._ui["user_name"] = name
            eng.save_ui_settings()
            self.show_secrets_gate()

        ctk.CTkButton(frame, text=g("next"), font=FONT, width=220, command=proceed).pack(pady=16)

    def switch_language(self, code):
        eng._ui["language"] = code
        eng.save_ui_settings()

    # ---------- secrets gate ----------

    def show_secrets_gate(self):
        self.clear()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both")
        ctk.CTkLabel(frame, text=g("secrets_missing"), font=FONT,
                     wraplength=700).pack(pady=(90, 24))
        picked = {"path": None}
        label = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color="#93c5fd")
        label.pack()

        def pick():
            path = filedialog.askopenfilename(
                title=g("secrets_pick"),
                filetypes=[("JSON", "*.json"), ("All files", "*.*")])
            if path:
                picked["path"] = path
                label.configure(text=os.path.basename(path))
        ctk.CTkButton(frame, text=g("secrets_pick"), font=FONT,
                      command=pick).pack(pady=8)

        def proceed():
            if not picked["path"]:
                return
            secrets_name = os.path.basename(picked["path"])
            dest_name = secrets_name if secrets_name.startswith("client_secrets") \
                else "client_secrets.json"
            dest = eng.data_file_path(dest_name)
            if not os.path.exists(dest):
                shutil.copy(picked["path"], dest)
            self.show_profiles()
        ctk.CTkButton(frame, text=g("next"), font=FONT, width=220,
                      command=proceed).pack(pady=12)

    # ---------- profiles ----------

    def show_profiles(self):
        self.clear()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both")
        ctk.CTkLabel(frame, text=g("profile_title"),
                     font=("Segoe UI", 22, "bold")).pack(pady=(50, 20))
        profiles = eng.load_channel_profiles()
        selected = {"id": None}
        buttons = {}

        def select(profile):
            selected["id"] = profile["profile_id"]
            for pid, btn in buttons.items():
                btn.configure(border_width=3 if pid == selected["id"] else 0)

        for profile in profiles["profiles"]:
            name = profile.get("channel_title") or profile.get("display_name")
            btn = ctk.CTkButton(frame, text=name, font=FONT, width=480, height=46,
                                border_width=0, fg_color="transparent",
                                text_color=("gray10", "#DCE4EE"),
                                hover_color=("gray70", "gray30"),
                                command=lambda p=profile: select(p))
            btn.pack(pady=4)
            buttons[profile["profile_id"]] = btn

        ctk.CTkLabel(frame, text=g("profile_name"), font=FONT).pack(pady=(30, 4))
        name_entry = ctk.CTkEntry(frame, width=480, font=FONT)
        name_entry.pack()
        secrets = {"path": None}
        secrets_label = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color="#93c5fd")
        secrets_label.pack()

        def pick_secrets():
            path = filedialog.askopenfilename(title=g("secrets_pick"),
                                              filetypes=[("JSON", "*.json")])
            if path:
                secrets["path"] = path
                secrets_label.configure(text=os.path.basename(path))
        ctk.CTkButton(frame, text=g("profile_add"), font=FONT_SMALL,
                      command=pick_secrets).pack(pady=(12, 4))

        def proceed():
            profile = None
            if selected["id"]:
                profile = next(p for p in profiles["profiles"]
                               if p["profile_id"] == selected["id"])
            elif secrets["path"] and name_entry.get().strip():
                profile = create_profile_gui(name_entry.get().strip(), secrets["path"])
            if profile:
                self.authorize(profile)
        ctk.CTkButton(frame, text=g("profile_continue"), font=FONT, width=280,
                      command=proceed).pack(pady=16)

    def authorize(self, profile):
        self.clear()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both")
        ctk.CTkLabel(frame, text=g("auth_opening"), font=FONT,
                     wraplength=650).pack(expand=True)
        status = ctk.CTkLabel(frame, text="", font=FONT_SMALL)
        status.pack(pady=16)
        ctk.CTkButton(frame, text=g("back"), font=FONT,
                      command=self.show_profiles).pack()

        def worker():
            try:
                youtube = eng.authenticate(profile)
                eng.refresh_profile_identity(youtube, profile, eng.load_channel_profiles())
                self.profile = profile
                self.youtube = youtube
                self.after(0, self.show_main)
            except Exception as error:
                def fail():
                    status.configure(text=g("auth_failed").format(error=error),
                                     text_color="#f87171")
                self.after(0, fail)
        threading.Thread(target=worker, daemon=True).start()

    # ---------- main window ----------

    def show_main(self):
        self.clear()
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(expand=True, fill="both")
        sidebar = ctk.CTkFrame(shell, width=230)
        sidebar.pack(side="left", fill="y", padx=14, pady=14)
        content = ctk.CTkFrame(shell)
        content.pack(side="right", expand=True, fill="both", padx=(0, 14), pady=14)

        def open_tab(handler):
            for widget in content.winfo_children():
                widget.destroy()
            handler(content)

        for label, handler in (
                (g("tab_translate"), self.show_translate),
                (g("tab_playlists"), self.show_playlists),
                (g("tab_schedule"), self.show_schedule),
                (g("tab_settings"), self.show_settings),
                (g("tab_profile"), self.show_profiles)):
            ctk.CTkButton(sidebar, text=label, font=FONT, anchor="w", height=44,
                          command=lambda h=handler: open_tab(h)).pack(pady=6, padx=10, fill="x")
        open_tab(self.show_translate)

    # ---------- translate tab ----------

    def show_translate(self, content):
        frame = ctk.CTkFrame(content, fg_color="transparent")
        frame.pack(expand=True, fill="both")

        ctk.CTkLabel(frame, text=g("tr_mode"), font=FONT_SMALL).pack(anchor="w")
        mode = ctk.StringVar(value=g("tr_last"))
        links_label = ctk.CTkLabel(frame, text=g("tr_links"), font=FONT_SMALL)
        links_box = ctk.CTkTextbox(frame, height=80, font=FONT_SMALL)

        def on_mode(value):
            if value == g("tr_specific"):
                links_label.pack(anchor="w", pady=(10, 2))
                links_box.pack(fill="x", pady=(0, 10))
            else:
                links_label.pack_forget()
                links_box.pack_forget()
        ctk.CTkSegmentedButton(frame, values=[g("tr_last"), g("tr_specific"), g("tr_all")],
                               command=on_mode, variable=mode,
                               font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text=g("tr_type"), font=FONT_SMALL).pack(anchor="w")
        vtype = ctk.StringVar(value=g("tr_long"))
        ctk.CTkSegmentedButton(frame, values=[g("tr_long"), g("tr_short")],
                               variable=vtype, font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text=g("tr_source"), font=FONT_SMALL).pack(anchor="w")
        source = ctk.StringVar(value=g("tr_source_video"))
        manual = ctk.CTkFrame(frame, fg_color="transparent")
        ctk.CTkLabel(manual, text=g("tr_manual_title"), font=FONT_SMALL).pack(anchor="w")
        title_entry = ctk.CTkEntry(manual, font=FONT_SMALL)
        title_entry.pack(fill="x", pady=(2, 8))
        ctk.CTkLabel(manual, text=g("tr_manual_desc"), font=FONT_SMALL).pack(anchor="w")
        desc_box = ctk.CTkTextbox(manual, height=90, font=FONT_SMALL)
        desc_box.pack(fill="x", pady=(2, 0))

        def on_source(value):
            if value == g("tr_source_manual"):
                manual.pack(fill="x", pady=(0, 12))
            else:
                manual.pack_forget()
        ctk.CTkOptionMenu(frame, values=[g("tr_source_video"), g("tr_source_manual")],
                          command=on_source, variable=source,
                          font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text=g("tr_parts"), font=FONT_SMALL).pack(anchor="w")
        parts = ctk.StringVar(value=g("parts_all"))
        ctk.CTkSegmentedButton(frame, values=[g("parts_all"), g("parts_titles"), g("parts_descs")],
                               variable=parts, font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        opts = ctk.CTkFrame(frame, fg_color="transparent")
        opts.pack(fill="x")
        add_pl = ctk.CTkCheckBox(opts, text=g("pl_defaults"), font=FONT_SMALL)
        add_pl.pack(side="left", padx=(0, 24))
        sched_flag = ctk.CTkCheckBox(opts, text=g("set_ask_schedule"), font=FONT_SMALL)
        sched_flag.pack(side="left")
        date_entry = ctk.CTkEntry(opts, width=120, placeholder_text=g("sched_date"),
                                  font=FONT_SMALL)
        date_entry.pack(side="left", padx=12)

        start_btn = ctk.CTkButton(frame, text=g("tr_start"), font=FONT_BOLD, height=46,
                                  command=lambda: self.start_translation(
                                      mode.get(), vtype.get(), links_box.get("1.0", "end"),
                                      source.get(), title_entry.get(),
                                      desc_box.get("1.0", "end"), parts.get(),
                                      add_pl.get(), sched_flag.get(), date_entry.get(),
                                      start_btn))
        start_btn.pack(fill="x", pady=12)

        self.lang_labels = {}
        lang_row = ctk.CTkFrame(frame, fg_color="transparent")
        lang_row.pack(fill="x")
        for code in eng.get_profile_languages(self.profile):
            if code == "en":
                continue
            label = ctk.CTkLabel(lang_row, text=f"{code}: …", font=FONT_SMALL)
            label.pack(side="left", padx=(0, 12))
            self.lang_labels[code] = label

        self.log_box = ctk.CTkTextbox(frame, height=190, font=FONT_SMALL)
        self.log_box.pack(expand=True, fill="both", pady=(8, 0))
        self.log_box.configure(state="disabled")

    def start_translation(self, mode_name, type_name, links_text, source_name,
                          manual_title, manual_desc, parts_name, add_playlists,
                          do_schedule, date_text, button):
        button.configure(state="disabled")
        self.lang_labels = getattr(self, "lang_labels", {})
        mode = {g("tr_last"): "last", g("tr_specific"): "specific", g("tr_all"): "all"}[mode_name]
        want_short = type_name == g("tr_short")
        parts = {g("parts_all"): ("title", "description"),
                 g("parts_titles"): ("title",),
                 g("parts_descs"): ("description",)}[parts_name]
        manual = source_name == g("tr_source_manual")
        links = [line.strip() for line in links_text.splitlines() if line.strip()] \
            if mode == "specific" else []
        langs = [code for code in eng.get_profile_languages(self.profile) if code != "en"]

        if self.log_box and self.log_box.winfo_exists():
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.configure(state="disabled")
        for label in self.lang_labels.values():
            label.configure(text=f"…", text_color="#93c5fd")

        def worker():
            try:
                videos, durations = eng.get_channel_videos(self.youtube)
                videos.sort(key=lambda x: x["snippet"]["publishedAt"], reverse=True)
                if mode == "last":
                    targets = eng._pick_translation_targets(
                        videos, durations, "last_short" if want_short else "last_long")
                elif mode == "all":
                    targets = eng._pick_translation_targets(
                        videos, durations, "all_short" if want_short else "all_long")
                else:
                    targets = [eng.extract_video_id(link) for link in links]
                    targets = [v for v in targets if v]
                if not targets:
                    self.log(g("tr_no_matches"))
                    return
                self.log(g("tr_found").format(n=len(targets)))
                for video_id in targets:
                    try:
                        metadata = eng.fetch_video_source_metadata(self.youtube, video_id)
                    except Exception as error:
                        self.log(f"❌ {error}")
                        continue
                    if manual:
                        if manual_title.strip():
                            metadata["title"] = manual_title.strip()
                        if manual_desc.strip():
                            metadata["description"] = eng.normalize_description(manual_desc)
                    eng.save_json_file(eng.METADATA_FILE, metadata)
                    self.log(f"🎬 {video_id} — {metadata['title']}")
                    try:
                        eng.localize_metadata_via_llm(metadata, langs, parts, progress=self.progress)
                    except Exception as error:
                        self.log(f"❌ {error}")
                        continue
                    localizations = eng.load_json_file(eng.LOCALIZATIONS_FILE)
                    try:
                        eng.update_video_metadata(
                            self.youtube, video_id,
                            metadata.get("title"), metadata.get("description"), localizations)
                        self.log(eng.t("video_updated").format(id=video_id))
                    except Exception as error:
                        self.log(f"❌ {error}")
                        continue
                    if add_playlists:
                        for pl_id in self.profile.get("default_playlists", []):
                            try:
                                eng.add_video_to_playlist(self.youtube, video_id, pl_id)
                                self.log(f"➕ {pl_id}")
                            except Exception as error:
                                self.log(f"❌ {error}")
                    if do_schedule:
                        try:
                            publish_date = datetime.strptime(date_text.strip(), "%d%m%y")
                            publish_datetime, _ = eng.to_publish_datetime(
                                publish_date, eng.load_calendar(self.profile))
                            eng.set_publishAt(self.youtube, video_id, publish_datetime)
                        except ValueError:
                            self.log("⚠️ ddmmyy")
                self.log(g("tr_done_all"))
            except Exception as error:
                self.log(f"❌ {error}")
            finally:
                self.after(0, lambda: button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def progress(self, state, code, detail=""):
        self.lang_status(code, state, detail)
        if state in ("ok", "fail"):
            self.log(f"{'✅' if state == 'ok' else '❌'} {code} {detail}")

    # ---------- playlists tab ----------

    def show_playlists(self, content):
        frame = ctk.CTkFrame(content, fg_color="transparent")
        frame.pack(expand=True, fill="both")

        ctk.CTkLabel(frame, text=g("pl_defaults"), font=FONT_SMALL).pack(anchor="w")
        rows = ctk.CTkFrame(frame, fg_color="transparent")
        rows.pack(fill="x", pady=(4, 12))

        def refresh():
            for widget in rows.winfo_children():
                widget.destroy()
            for pl in self.profile.get("playlists", []):
                row = ctk.CTkFrame(rows, fg_color="transparent")
                row.pack(fill="x", pady=2)
                var = ctk.BooleanVar(value=pl["id"] in self.profile.get("default_playlists", []))

                def toggle(pid=pl["id"], v=var):
                    ds = self.profile.setdefault("default_playlists", [])
                    if v.get() and pid not in ds:
                        ds.append(pid)
                    elif not v.get() and pid in ds:
                        ds.remove(pid)
                    eng.save_channel_profiles(eng.load_channel_profiles())

                ctk.CTkCheckBox(row, text=f"{pl['name']} — {pl['id']}", variable=var,
                                command=toggle, font=FONT_SMALL).pack(side="left")

                def remove(pid=pl["id"]):
                    self.profile["playlists"] = [p for p in self.profile["playlists"]
                                                 if p["id"] != pid]
                    ds = self.profile.setdefault("default_playlists", [])
                    if pid in ds:
                        ds.remove(pid)
                    eng.save_channel_profiles(eng.load_channel_profiles())
                    refresh()
                ctk.CTkButton(row, text="✕", width=36, fg_color="#7f1d1d",
                              command=remove).pack(side="right")
        refresh()

        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        add_row.pack(fill="x", pady=(0, 12))
        name_entry = ctk.CTkEntry(add_row, placeholder_text=g("pl_name"), width=220,
                                  font=FONT_SMALL)
        name_entry.pack(side="left", padx=(0, 8))
        id_entry = ctk.CTkEntry(add_row, placeholder_text=g("pl_id"), font=FONT_SMALL)
        id_entry.pack(side="left", expand=True, fill="x", padx=(0, 8))

        def add_playlist():
            raw = id_entry.get().strip()
            playlist_id = eng.parse_playlist_id(raw)
            if not playlist_id or any(pl["id"] == playlist_id
                                      for pl in self.profile["playlists"]):
                return
            title = eng.fetch_playlist_title(self.youtube, playlist_id)
            name = name_entry.get().strip() or title or playlist_id
            self.profile["playlists"].append({"id": playlist_id, "name": name})
            eng.save_channel_profiles(eng.load_channel_profiles())
            refresh()
        ctk.CTkButton(add_row, text=g("pl_add_playlist"), font=FONT_SMALL,
                      command=add_playlist).pack(side="left")

        ctk.CTkLabel(frame, text=g("pl_add_video"), font=FONT_BOLD).pack(anchor="w",
                                                                         pady=(16, 4))
        video_row = ctk.CTkFrame(frame, fg_color="transparent")
        video_row.pack(fill="x")
        video_entry = ctk.CTkEntry(video_row, placeholder_text=g("pl_video_link"),
                                   font=FONT_SMALL)
        video_entry.pack(side="left", expand=True, fill="x", padx=(0, 8))
        chosen = {"ids": list(self.profile.get("default_playlists", []))}
        pl_label = ctk.CTkLabel(frame, text="—", font=FONT_SMALL, justify="left")
        pl_label.pack(anchor="w", pady=4)

        def render_chosen():
            names = {pl["id"]: pl["name"] for pl in self.profile.get("playlists", [])}
            pl_label.configure(text=", ".join(
                names.get(pid, pid) for pid in chosen["ids"]) or "—")

        def pick_dialog():
            top = ctk.CTkToplevel(self)
            top.title(g("pl_target_pick"))
            top.geometry("560x420")
            top.grab_set()
            vars_ = {}

            def apply():
                chosen["ids"] = [pid for pid, var in vars_.items() if var.get()]
                render_chosen()
                top.destroy()
            for pl in self.profile.get("playlists", []):
                var = ctk.BooleanVar(value=pl["id"] in chosen["ids"])
                vars_[pl["id"]] = var
                ctk.CTkCheckBox(top, text=f"{pl['name']} — {pl['id']}", variable=var,
                                font=FONT).pack(anchor="w", padx=20, pady=6)
            ctk.CTkButton(top, text=g("save"), font=FONT, command=apply).pack(pady=14)
        ctk.CTkButton(video_row, text="▾ " + g("pl_target_pick"), font=FONT_SMALL,
                      command=pick_dialog).pack(side="left")
        render_chosen()

        def add_video():
            video_id = eng.extract_video_id(video_entry.get())
            if not video_id or not chosen["ids"]:
                return
            added = 0
            for pl_id in chosen["ids"]:
                try:
                    eng.add_video_to_playlist(self.youtube, video_id, pl_id)
                    added += 1
                except Exception as error:
                    self.log(f"❌ {error}")
            pl_label.configure(text=g("pl_added").format(n=added))
        ctk.CTkButton(frame, text=g("pl_add_video"), font=FONT,
                      command=add_video).pack(anchor="w")

    # ---------- schedule tab ----------

    def show_schedule(self, content):
        frame = ctk.CTkFrame(content, fg_color="transparent")
        frame.pack(expand=True, fill="both")
        link_entry = ctk.CTkEntry(frame, placeholder_text=g("sched_link"), font=FONT)
        link_entry.pack(fill="x")
        date_entry = ctk.CTkEntry(frame, placeholder_text=g("sched_date"), font=FONT)
        date_entry.pack(fill="x", pady=8)
        status = ctk.CTkLabel(frame, text="", font=FONT_SMALL)
        status.pack(pady=6)

        def schedule():
            video_id = eng.extract_video_id(link_entry.get())
            if not video_id:
                return
            try:
                publish_date = datetime.strptime(date_entry.get().strip(), "%d%m%y")
                publish_datetime, publish_time = eng.to_publish_datetime(
                    publish_date, eng.load_calendar(self.profile))
            except ValueError:
                status.configure(text=g("sched_bad_date"), text_color="#fbbf24")
                return
            if eng.set_publishAt(self.youtube, video_id, publish_datetime):
                status.configure(text=g("sched_done").format(
                    date=publish_datetime.strftime("%d.%m.%Y %H:%M")), text_color="#4ade80")
        ctk.CTkButton(frame, text=g("sched_set"), font=FONT, command=schedule).pack(anchor="w")

    # ---------- settings tab ----------

    def show_settings(self, content):
        frame = ctk.CTkFrame(content, fg_color="transparent")
        frame.pack(expand=True, fill="both")

        ctk.CTkLabel(frame, text=g("set_language"), font=FONT_SMALL).pack(anchor="w")
        names = [GUI_STRINGS[c]["lang_name"] for c in LANG_CODES]
        codes = {GUI_STRINGS[c]["lang_name"]: c for c in LANG_CODES}
        lang_menu = ctk.CTkOptionMenu(frame, values=names, font=FONT_SMALL,
                                      command=lambda v: (self.switch_language(codes[v]),
                                                         self.show_main()))
        lang_menu.set(GUI_STRINGS[eng._ui.get("language") or "en"]["lang_name"])
        lang_menu.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text=g("set_name"), font=FONT_SMALL).pack(anchor="w")
        name_entry = ctk.CTkEntry(frame, font=FONT_SMALL)
        name_entry.insert(0, eng._ui.get("user_name", ""))
        name_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text=g("set_parallel"), font=FONT_SMALL).pack(anchor="w")
        llm_cfg = eng.load_local_llm_config()
        current = str(llm_cfg.get("max_parallel_languages", "auto"))
        values = [g("set_auto")] + [str(i) for i in range(1, 11)]
        par_menu = ctk.CTkOptionMenu(frame, values=values, font=FONT_SMALL)
        par_menu.set(current if current in values else g("set_auto"))
        par_menu.pack(fill="x", pady=(0, 10))

        for flag_key, label_key in (("ask_playlists", "set_ask_playlists"),
                                    ("ask_schedule", "set_ask_schedule")):
            var = ctk.BooleanVar(value=bool(eng._ui.get(flag_key, True)))

            def toggle(v=var, k=flag_key):
                eng._ui[k] = v.get()
                eng.save_ui_settings()
            ctk.CTkCheckBox(frame, text=g(label_key), variable=var, command=toggle,
                            font=FONT_SMALL).pack(anchor="w", pady=4)

        def save_common():
            eng._ui["user_name"] = name_entry.get().strip()
            llm = eng.load_local_llm_config()
            raw = par_menu.get()
            llm["max_parallel_languages"] = "auto" if raw == g("set_auto") else int(raw)
            eng.save_json_file("local_llm.json", llm)
            eng.save_ui_settings()
            self.show_main()
        ctk.CTkButton(frame, text=g("save"), font=FONT, command=save_common).pack(anchor="w")

        ctk.CTkLabel(frame, text=g("api_title"),
                     font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(26, 8))
        reg = eng.load_provider_registry()
        rows = ctk.CTkFrame(frame, fg_color="transparent")
        rows.pack(fill="x")
        for provider in reg["providers"]:
            row = ctk.CTkFrame(rows, fg_color="transparent")
            row.pack(fill="x", pady=2)
            if provider["id"] == reg.get("active"):
                mark = "●"
            elif provider["id"] == reg.get("backup"):
                mark = "○"
            else:
                mark = " "
            kind = g("api_online") if provider.get("auth") else g("api_local")
            label_text = (f"{mark} {provider['name']} [{kind}] — {provider.get('model', 'auto')} "
                          f"({g('api_keys_n').format(n=len(provider.get('api_keys', [])))})")
            ctk.CTkLabel(row, text=label_text, font=FONT_SMALL).pack(side="left")

            def activate(p=provider):
                reg["active"] = p["id"]
                eng.save_provider_registry(reg)
                self.show_main()
            ctk.CTkButton(row, text="●", width=40, command=activate).pack(side="right", padx=2)

            def remove(p=provider):
                reg["providers"].remove(p)
                if reg.get("active") == p["id"] and reg["providers"]:
                    reg["active"] = reg["providers"][0]["id"]
                if reg.get("backup") == p["id"]:
                    reg["backup"] = None
                eng.save_provider_registry(reg)
                self.show_main()
            ctk.CTkButton(row, text="✕", width=40, fg_color="#7f1d1d",
                          command=remove).pack(side="right", padx=2)


def main():
    try:
        saved = eng.load_json_file(eng.UI_SETTINGS_FILE)
        if saved.get("ui_language") in eng.STRINGS:
            eng._ui["language"] = saved["ui_language"]
        eng._ui["user_name"] = str(saved.get("user_name", "")).strip()
        eng._ui["ask_playlists"] = bool(saved.get("ask_playlists", True))
        eng._ui["ask_schedule"] = bool(saved.get("ask_schedule", True))
    except (FileNotFoundError, ValueError):
        pass
    if not eng._ui["language"] or not eng._ui["user_name"]:
        eng._ui["language"] = None  # force the in-app onboarding screens
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
