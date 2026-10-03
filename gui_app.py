"""YouTube Metadata Translator — desktop GUI (customtkinter, Windows/macOS/Linux)."""
import os
import re
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
FONT_TITLE = ("Segoe UI", 22, "bold")
LANG_CODES = ("en", "uk", "ru")
COLOR_OK = "#4ade80"
COLOR_FAIL = "#f87171"
COLOR_RETRY = "#fbbf24"
COLOR_INFO = "#93c5fd"

GUI_STRINGS = {
    "en": {
        "app_title": "YouTube Metadata Translator",
        "lang_name": "English",
        "tab_translate": "Translate", "tab_playlists": "Playlists",
        "tab_schedule": "Publishing", "tab_settings": "Settings", "tab_profile": "Channels",
        "choose_language": "Interface language", "your_name": "Your name",
        "next": "Next", "save": "Save", "back": "Back", "cancel": "Cancel",
        "secrets_missing": "No client_secrets file found. Pick the JSON downloaded from Google Cloud.",
        "secrets_pick": "Pick client_secrets.json",
        "profile_title": "Channels — click one to sign in",
        "profile_name": "Name for the new channel profile",
        "profile_add": "Add a new channel",
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
        "sched_set": "Schedule", "sched_done": "✓ Scheduled for {date}",
        "sched_bad_date": "Invalid date",
        "set_interface": "Interface", "set_language": "Language", "set_name": "Your name",
        "set_parallel": "Parallel translations", "set_auto": "Auto", "set_saved": "✓ Saved",
        "set_ask_playlists": "Ask about playlists after translation",
        "set_ask_schedule": "Ask about deferred publishing after translation",
        "set_languages": "Translation languages",
        "lang_custom_code": "Custom code (e.g. pt-BR)",
        "lang_custom_name": "Name for the AI (e.g. Brazilian Portuguese)",
        "lang_add": "Add language",
        "presets_title": "Language presets",
        "preset_apply": "Apply", "preset_save": "Save current as preset",
        "preset_delete": "Delete preset", "preset_name_prompt": "Preset name:",
        "preset_none": "No presets yet.",
        "api_title": "API providers", "api_add": "Add provider", "api_activate": "Make active",
        "api_online": "Online", "api_local": "Local", "api_keys_n": "{n} key(s)",
        "api_kind": "Type", "api_name": "Display name", "api_base": "Base URL",
        "api_keys": "API keys (comma-separated)", "api_model": "Model",
        "api_fetch_models": "Fetch models",
        "api_no_models": "Couldn't fetch the model list — type the name manually.",
        "api_need_url": "A base URL is required for an online provider.",
        "provider_new_title": "— Adding a provider —",
        "lang_search": "Search language…",
        "tr_targets": "Translating into: {names}",
        "provider_edit_title": "— Editing provider: {name} —",
    },
    "uk": {
        "app_title": "YouTube Metadata Translator",
        "lang_name": "Українська",
        "tab_translate": "Переклад", "tab_playlists": "Плейлисти",
        "tab_schedule": "Публікація", "tab_settings": "Налаштування", "tab_profile": "Канали",
        "choose_language": "Мова інтерфейсу", "your_name": "Ваше ім'я",
        "next": "Далі", "save": "Зберегти", "back": "Назад", "cancel": "Скасувати",
        "secrets_missing": "Не знайдено client_secrets. Виберіть JSON, завантажений з Google Cloud.",
        "secrets_pick": "Виберіть client_secrets.json",
        "profile_title": "Канали — клацніть, щоб увійти",
        "profile_name": "Назва нового профілю каналу",
        "profile_add": "Додати новий канал",
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
        "sched_set": "Запланувати", "sched_done": "✓ Заплановано на {date}",
        "sched_bad_date": "Некоректна дата",
        "set_interface": "Інтерфейс", "set_language": "Мова", "set_name": "Ваше ім'я",
        "set_parallel": "Одночасні переклади", "set_auto": "Авто", "set_saved": "✓ Збережено",
        "set_ask_playlists": "Питати про плейлисти після перекладу",
        "set_ask_schedule": "Питати про відкладену публікацію після перекладу",
        "set_languages": "Мови перекладу",
        "lang_custom_code": "Свій код (наприклад pt-BR)",
        "lang_custom_name": "Назва для нейромережі (наприклад Brazilian Portuguese)",
        "lang_add": "Додати мову",
        "presets_title": "Пресети мов",
        "preset_apply": "Застосувати", "preset_save": "Зберегти поточний як пресет",
        "preset_delete": "Видалити пресет", "preset_name_prompt": "Назва пресета:",
        "preset_none": "Пресетів ще немає.",
        "api_title": "API-провайдери", "api_add": "Додати провайдера", "api_activate": "Зробити активним",
        "api_online": "Онлайн", "api_local": "Локальний", "api_keys_n": "ключів: {n}",
        "api_kind": "Тип", "api_name": "Ім'я для показу", "api_base": "Base URL",
        "api_keys": "API-ключі через кому", "api_model": "Модель",
        "api_fetch_models": "Отримати моделі",
        "api_no_models": "Не вдалося отримати список моделей — введіть назву вручну.",
        "api_need_url": "Для онлайн-провайдера потрібен base URL.",
        "provider_new_title": "— Додавання провайдера —",
        "lang_search": "Пошук мови…",
        "tr_targets": "Перекладаємо на: {names}",
        "provider_edit_title": "— Зміна провайдера: {name} —",
    },
    "ru": {
        "app_title": "YouTube Metadata Translator",
        "lang_name": "Русский",
        "tab_translate": "Перевод", "tab_playlists": "Плейлисты",
        "tab_schedule": "Публикация", "tab_settings": "Настройки", "tab_profile": "Каналы",
        "choose_language": "Язык интерфейса", "your_name": "Твоё имя",
        "next": "Далее", "save": "Сохранить", "back": "Назад", "cancel": "Отмена",
        "secrets_missing": "Не найден client_secrets. Выбери JSON, скачанный из Google Cloud.",
        "secrets_pick": "Выбери client_secrets.json",
        "profile_title": "Каналы — кликни, чтобы войти",
        "profile_name": "Название нового профиля канала",
        "profile_add": "Добавить новый канал",
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
        "sched_set": "Запланировать", "sched_done": "✓ Запланировано на {date}",
        "sched_bad_date": "Некорректная дата",
        "set_interface": "Интерфейс", "set_language": "Язык", "set_name": "Твоё имя",
        "set_parallel": "Одновременные переводы", "set_auto": "Авто", "set_saved": "✓ Сохранено",
        "set_ask_playlists": "Спрашивать про плейлисты после перевода",
        "set_ask_schedule": "Спрашивать про отложенную публикацию после перевода",
        "set_languages": "Языки перевода",
        "lang_custom_code": "Свой код (например pt-BR)",
        "lang_custom_name": "Название для нейросети (например Brazilian Portuguese)",
        "lang_add": "Добавить язык",
        "presets_title": "Пресеты языков",
        "preset_apply": "Применить", "preset_save": "Сохранить текущий как пресет",
        "preset_delete": "Удалить пресет", "preset_name_prompt": "Название пресета:",
        "preset_none": "Пресетов ещё нет.",
        "api_title": "API-провайдеры", "api_add": "Добавить провайдера", "api_activate": "Сделать активным",
        "api_online": "Онлайн", "api_local": "Локальный", "api_keys_n": "ключей: {n}",
        "api_kind": "Тип", "api_name": "Отображаемое имя", "api_base": "Base URL",
        "api_keys": "API-ключи через запятую", "api_model": "Модель",
        "api_fetch_models": "Получить модели",
        "api_no_models": "Не удалось получить список моделей — введи название вручную.",
        "api_need_url": "Для онлайн-провайдера нужен base URL.",
        "provider_new_title": "— Добавление провайдера —",
        "lang_search": "Поиск языка…",
        "tr_targets": "Переводим на: {names}",
        "provider_edit_title": "— Изменение провайдера: {name} —",
    },
}


def g(key, **kwargs):
    lang = eng._ui.get("language") or "en"
    text = GUI_STRINGS.get(lang, GUI_STRINGS["en"]).get(key) or GUI_STRINGS["en"][key]
    return text.format(**kwargs) if kwargs else text


# Localized language names for the UI (native names come from the engine catalog).
LANG_NAME_LOCALIZATION = {
    "uk": {
        "af": "Африкаанс", "az": "Азербайджанська", "id": "Індонезійська",
        "ms": "Малайська", "bs": "Боснійська", "ca": "Каталонська", "cs": "Чеська",
        "cy": "Валлійська", "da": "Данська", "de": "Німецька", "et": "Естонська",
        "en": "Англійська", "en-CA": "Англійська (Канада)", "en-GB": "Англійська (Велика Британія)",
        "en-IN": "Англійська (Індія)", "en-US": "Англійська (США)", "es": "Іспанська",
        "es-419": "Іспанська (Латинська Америка)", "es-US": "Іспанська (США)",
        "eu": "Баскська", "fil": "Філіппінська", "fr": "Французька",
        "fr-CA": "Французька (Канада)", "gl": "Галісійська", "gu": "Гуджараті",
        "hr": "Хорватська", "is": "Ісландська", "it": "Італійська", "jv": "Яванська",
        "kn": "Каннада", "la": "Латина", "lv": "Латиська", "lt": "Литовська",
        "hu": "Угорська", "nl": "Нідерландська", "ne": "Непальська", "no": "Норвезька",
        "or": "Орія", "pa": "Пенджабська", "pl": "Польська", "pt": "Португальська (Бразилія)",
        "pt-PT": "Португальська (Португалія)", "ro": "Румунська", "rm": "Ретороманська",
        "si": "Сингальська", "sk": "Словацька", "sl": "Словенська", "fi": "Фінська",
        "sv": "Шведська", "sw": "Суахілі", "tl": "Тагальська", "ta": "Тамільська",
        "te": "Телугу", "th": "Тайська", "vi": "В'єтнамська", "tr": "Турецька",
        "uk": "Українська", "ur": "Урду", "zh-Hans": "Китайська (спрощена)",
        "zh-Hant": "Китайська (традиційна)", "zh-TW": "Китайська (Тайвань)",
        "zu": "Зулу", "el": "Грецька", "bg": "Болгарська", "ru": "Російська",
        "sr": "Сербська", "mk": "Македонська", "kk": "Казахська", "ky": "Киргизька",
        "hy": "Вірменська", "ka": "Грузинська", "mn": "Монгольська", "my": "Бірманська",
        "km": "Кхмерська", "lo": "Лаоська", "he": "Іврит", "ar": "Арабська",
        "fa": "Перська", "sd": "Сіндхі", "am": "Амхарська", "yo": "Йоруба",
        "ha": "Хауса", "ig": "Ігбо", "qu": "Кечуа", "nso": "Педі",
        "bn": "Бенгальська", "hi": "Гінді", "ja": "Японська", "ko": "Корейська",
        "so": "Сомалійська", "sq": "Албанська",
    },
    "ru": {
        "af": "Африкаанс", "az": "Азербайджанский", "id": "Индонезийский",
        "ms": "Малайский", "bs": "Боснийский", "ca": "Каталанский", "cs": "Чешский",
        "cy": "Валлийский", "da": "Датский", "de": "Немецкий", "et": "Эстонский",
        "en": "Английский", "en-CA": "Английский (Канада)", "en-GB": "Английский (Великобритания)",
        "en-IN": "Английский (Индия)", "en-US": "Английский (США)", "es": "Испанский",
        "es-419": "Испанский (Латинская Америка)", "es-US": "Испанский (США)",
        "eu": "Баскский", "fil": "Филиппинский", "fr": "Французский",
        "fr-CA": "Французский (Канада)", "gl": "Галисийский", "gu": "Гуджарати",
        "hr": "Хорватский", "is": "Исландский", "it": "Итальянский", "jv": "Яванский",
        "kn": "Каннада", "la": "Латынь", "lv": "Латышский", "lt": "Литовский",
        "hu": "Венгерский", "nl": "Нидерландский", "ne": "Непальский", "no": "Норвежский",
        "or": "Ория", "pa": "Панджаби", "pl": "Польский", "pt": "Португальский (Бразилия)",
        "pt-PT": "Португальский (Португалия)", "ro": "Румынский", "rm": "Ретороманский",
        "si": "Сингальский", "sk": "Словацкий", "sl": "Словенский", "fi": "Финский",
        "sv": "Шведский", "sw": "Суахили", "tl": "Тагальский", "ta": "Тамильский",
        "te": "Телугу", "th": "Тайский", "vi": "Вьетнамский", "tr": "Турецкий",
        "uk": "Украинский", "ur": "Урду", "zh-Hans": "Китайский (упрощённый)",
        "zh-Hant": "Китайский (традиционный)", "zh-TW": "Китайский (Тайвань)",
        "zu": "Зулу", "el": "Греческий", "bg": "Болгарский", "ru": "Русский",
        "sr": "Сербский", "mk": "Македонский", "kk": "Казахский", "ky": "Киргизский",
        "hy": "Армянский", "ka": "Грузинский", "mn": "Монгольский", "my": "Бирманский",
        "km": "Кхмерский", "lo": "Лаосский", "he": "Иврит", "ar": "Арабский",
        "fa": "Персидский", "sd": "Синдхи", "am": "Амхарский", "yo": "Йоруба",
        "ha": "Хауса", "ig": "Игбо", "qu": "Кечуа", "nso": "Педи",
        "bn": "Бенгальский", "hi": "Хинди", "ja": "Японский", "ko": "Корейский",
        "so": "Сомалийский", "sq": "Албанский",
    },
}


def lang_display(code):
    """Localized name for the UI language; native name as fallback."""
    localized = LANG_NAME_LOCALIZATION.get(eng._ui.get("language"), {}).get(code)
    if localized:
        return localized
    return eng.available_language_catalog().get(code, code)


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
        self.lang_states = {}
        self.sidebar_buttons = {}
        self.header_label = None
        self.tab_frames = {}
        # First run without saved language/name -> onboarding; otherwise jump
        # to the secrets gate (auto-skipped when data/ has client_secrets*).
        if not eng._ui.get("language") or not eng._ui.get("user_name"):
            self.show_onboarding()
        elif not eng.find_secrets_files():
            self.show_secrets_gate()
        else:
            self.show_profiles()

    # ---------- helpers ----------

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

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
        self.lang_states[code] = (state, detail)
        self.after(0, self._render_lang_states)

    def _render_lang_states(self):
        """One comma-separated line: German ✓, Español ⏳, 日本語 …"""
        if not (self.lang_label and self.lang_label.winfo_exists()):
            return
        marks = {"ok": "✓", "fail": "✗", "retry": "⏳", "start": "…"}
        chunks = [
            f"{lang_display(code)} {marks.get(state, '')} {detail}".strip()
            for code, (state, detail) in self.lang_states.items()
        ]
        self.lang_label.configure(text=", ".join(chunks))

    def switch_language(self, code):
        eng._ui["language"] = code
        eng.save_ui_settings()

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
        status = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color=COLOR_RETRY)
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

    # ---------- secrets gate ----------

    def show_secrets_gate(self):
        if eng.find_secrets_files():
            self.show_profiles()
            return
        self.clear()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both")
        ctk.CTkLabel(frame, text=g("secrets_missing"), font=FONT,
                     wraplength=700).pack(pady=(90, 24))
        picked = {"path": None}
        label = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color=COLOR_INFO)
        label.pack()

        def pick():
            path = filedialog.askopenfilename(
                title=g("secrets_pick"),
                filetypes=[("JSON", "*.json"), ("All files", "*.*")])
            if path:
                picked["path"] = path
                label.configure(text=os.path.basename(path))
        ctk.CTkButton(frame, text=g("secrets_pick"), font=FONT, command=pick).pack(pady=8)

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
        ctk.CTkButton(frame, text=g("next"), font=FONT, width=220, command=proceed).pack(pady=12)

    # ---------- profiles ----------

    def show_profiles(self):
        self.clear()
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True, fill="both")
        ctk.CTkLabel(frame, text=g("profile_title"), font=FONT_TITLE).pack(pady=(50, 24))
        profiles = eng.load_channel_profiles()["profiles"]

        # Clicking a channel signs in immediately (no extra Continue step).
        for profile in profiles:
            name = profile.get("channel_title") or profile.get("display_name")
            ctk.CTkButton(frame, text=name, font=FONT, width=480, height=46,
                          border_width=0, fg_color="transparent",
                          text_color=("gray10", "#DCE4EE"),
                          hover_color=("gray70", "gray30"),
                          command=lambda p=profile: self.authorize(p)).pack(pady=4)

        ctk.CTkButton(frame, text="＋ " + g("profile_add"), font=FONT, width=480, height=46,
                      command=lambda: self.add_channel_dialog()).pack(pady=(20, 0))

    def add_channel_dialog(self):
        top = ctk.CTkToplevel(self)
        top.title(g("profile_add"))
        top.geometry("560x360")
        top.grab_set()
        ctk.CTkLabel(top, text=g("profile_name"), font=FONT).pack(pady=(24, 4))
        name_entry = ctk.CTkEntry(top, width=440, font=FONT)
        name_entry.pack()
        secrets = {"path": None}
        secrets_label = ctk.CTkLabel(top, text="", font=FONT_SMALL, text_color=COLOR_INFO)
        secrets_label.pack(pady=6)

        def pick():
            path = filedialog.askopenfilename(title=g("secrets_pick"),
                                              filetypes=[("JSON", "*.json")])
            if path:
                secrets["path"] = path
                secrets_label.configure(text=os.path.basename(path))
        ctk.CTkButton(top, text=g("secrets_pick"), font=FONT_SMALL, command=pick).pack(pady=6)

        def save():
            if not secrets["path"]:
                secrets_label.configure(text=g("secrets_pick"), text_color=COLOR_RETRY)
                return
            name = name_entry.get().strip() or \
                os.path.splitext(os.path.basename(secrets["path"]))[0]
            top.destroy()
            self.authorize(create_profile_gui(name, secrets["path"]))
        ctk.CTkButton(top, text=g("save"), font=FONT, command=save).pack(pady=10)

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
            except Exception as error:
                message = str(error)

                def fail(message=message):
                    status.configure(text=g("auth_failed").format(error=message),
                                     text_color=COLOR_FAIL)
                self.after(0, fail)
                return
            self.profile = profile
            self.youtube = youtube
            self.after(0, self.show_main)
        threading.Thread(target=worker, daemon=True).start()

    # ---------- main window: persistent sidebar + tab frames ----------

    TAB_DEFS = (("translate", "tab_translate", "build_translate"),
                ("playlists", "tab_playlists", "build_playlists"),
                ("schedule", "tab_schedule", "build_schedule"),
                ("settings", "tab_settings", "build_settings"))

    def show_main(self):
        self.clear()
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(expand=True, fill="both")
        sidebar = ctk.CTkFrame(shell, width=230)
        sidebar.pack(side="left", fill="y", padx=14, pady=14)
        content = ctk.CTkFrame(shell)
        content.pack(side="right", expand=True, fill="both", padx=(0, 14), pady=14)
        self.content = content

        self.header_label = ctk.CTkLabel(
            sidebar, text=f"👋 {eng._ui.get('user_name', '')}",
            font=FONT_BOLD, wraplength=200)
        self.header_label.pack(pady=(14, 18), padx=10)

        self.tab_frames = {}
        self.sidebar_buttons = {}
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        for name, label_key, builder in self.TAB_DEFS:
            tab = ctk.CTkFrame(content, fg_color="transparent")
            tab.grid(row=0, column=0, sticky="nsew")
            self.tab_frames[name] = (tab, getattr(self, builder))
            btn = ctk.CTkButton(sidebar, text=g(label_key), font=FONT, anchor="w",
                                height=44, command=lambda n=name: self.open_tab(n))
            btn.pack(pady=6, padx=10, fill="x")
            self.sidebar_buttons[name] = (btn, label_key)
        self.open_tab("translate", rebuild=True)

    def open_tab(self, name, rebuild=False):
        tab, builder = self.tab_frames[name]
        if rebuild or not tab.winfo_children():
            for widget in tab.winfo_children():
                widget.destroy()
            builder(tab)
        tab.tkraise()
        self.current_tab = name

    def rebuild_tab(self, name):
        """Rebuild a single tab's content without touching the others."""
        tab, builder = self.tab_frames[name]
        for widget in tab.winfo_children():
            widget.destroy()
        builder(tab)

    def update_texts(self):
        """Refresh sidebar labels (called on language change)."""
        if not self.header_label:
            return
        self.header_label.configure(text=f"👋 {eng._ui.get('user_name', '')}")
        for name, (btn, label_key) in self.sidebar_buttons.items():
            btn.configure(text=g(label_key))

    def rebuild_tabs(self):
        """Rebuild every tab's content (after a language or data change)."""
        current = getattr(self, "current_tab", None) or "translate"
        for name in self.tab_frames:
            self.rebuild_tab(name)
        self.open_tab(current)

    def refresh_after_language_change(self):
        self.update_texts()
        self.rebuild_tabs()

    # ---------- translate tab ----------

    def build_translate(self, tab):
        frame = ctk.CTkFrame(tab, fg_color="transparent")
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
                               command=lambda v: (on_mode(v), save_state()),
                               variable=mode, font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text=g("tr_type"), font=FONT_SMALL).pack(anchor="w")
        vtype = ctk.StringVar(value=g("tr_long"))
        ctk.CTkSegmentedButton(frame, values=[g("tr_long"), g("tr_short")],
                               variable=vtype, command=lambda v: save_state(),
                               font=FONT_SMALL).pack(fill="x", pady=(0, 12))

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
            # Manual fields appear between the language row and the log.
            if value == g("tr_source_manual"):
                manual.pack(fill="x", pady=(0, 12), before=self.log_box)
            else:
                manual.pack_forget()
        ctk.CTkOptionMenu(frame, values=[g("tr_source_video"), g("tr_source_manual")],
                          command=lambda v: (on_source(v), save_state()),
                          variable=source, font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text=g("tr_parts"), font=FONT_SMALL).pack(anchor="w")
        parts = ctk.StringVar(value=g("parts_all"))
        ctk.CTkSegmentedButton(frame, values=[g("parts_all"), g("parts_titles"), g("parts_descs")],
                               variable=parts, command=lambda v: save_state(),
                               font=FONT_SMALL).pack(fill="x", pady=(0, 12))

        targets_label = ctk.CTkLabel(
            frame, text=g("tr_targets").format(
                names=", ".join(lang_display(c) for c in eng.get_profile_languages(self.profile)
                                if c != "en") or "—"),
            font=FONT_SMALL, justify="left", wraplength=900)
        targets_label.pack(anchor="w", pady=(0, 10))

        def save_state():
            eng._ui["ui_tr_mode"] = mode.get()
            eng._ui["ui_tr_type"] = vtype.get()
            eng._ui["ui_tr_source"] = source.get()
            eng._ui["ui_tr_parts"] = parts.get()
            eng._ui["ui_add_defaults"] = bool(add_pl.get())
            eng._ui["ui_sched"] = bool(sched_flag.get())
            eng._ui["ui_sched_date"] = date_entry.get()
            eng.save_ui_settings()

        def restore_state():
            saved_mode = eng._ui.get("ui_tr_mode")
            if saved_mode in (g("tr_last"), g("tr_specific"), g("tr_all")):
                mode.set(saved_mode)
                on_mode(saved_mode)
            saved_type = eng._ui.get("ui_tr_type")
            if saved_type in (g("tr_long"), g("tr_short")):
                vtype.set(saved_type)
            saved_source = eng._ui.get("ui_tr_source")
            if saved_source in (g("tr_source_video"), g("tr_source_manual")):
                source.set(saved_source)
                on_source(saved_source)
            saved_parts = eng._ui.get("ui_tr_parts")
            if saved_parts in (g("parts_all"), g("parts_titles"), g("parts_descs")):
                parts.set(saved_parts)
            if eng._ui.get("ui_add_defaults"):
                add_pl.select()
            if eng._ui.get("ui_sched"):
                sched_flag.select()
            saved_date = eng._ui.get("ui_sched_date")
            if saved_date:
                date_entry.insert(0, saved_date)

        opts = ctk.CTkFrame(frame, fg_color="transparent")
        opts.pack(fill="x")
        add_pl = ctk.CTkCheckBox(opts, text=g("pl_defaults"), font=FONT_SMALL,
                                 command=save_state)
        add_pl.pack(side="left", padx=(0, 24))
        sched_flag = ctk.CTkCheckBox(opts, text=g("set_ask_schedule"), font=FONT_SMALL,
                                   command=save_state)
        sched_flag.pack(side="left")
        date_entry = ctk.CTkEntry(opts, width=120, placeholder_text=g("sched_date"),
                                  font=FONT_SMALL)
        date_entry.pack(side="left", padx=12)
        date_entry.bind("<KeyRelease>", lambda e: save_state())

        start_btn = ctk.CTkButton(frame, text=g("tr_start"), font=FONT_BOLD, height=46,
                                  command=lambda: self.start_translation(
                                      mode.get(), vtype.get(), links_box.get("1.0", "end"),
                                      source.get(), title_entry.get(),
                                      desc_box.get("1.0", "end"), parts.get(),
                                      add_pl.get(), sched_flag.get(), date_entry.get(),
                                      start_btn))
        start_btn.pack(fill="x", pady=12)

        self.lang_states = {}
        self.lang_label = ctk.CTkLabel(frame, text="", font=FONT_SMALL,
                                       justify="left", wraplength=900)
        self.lang_label.pack(fill="x", pady=(10, 0))
        self._render_lang_states()

        self.log_box = ctk.CTkTextbox(frame, height=190, font=FONT_SMALL)
        self.log_box.pack(expand=True, fill="both", pady=(8, 0))
        self.log_box.configure(state="disabled")

    def start_translation(self, mode_name, type_name, links_text, source_name,
                          manual_title, manual_desc, parts_name, add_playlists,
                          do_schedule, date_text, button):
        button.configure(state="disabled")
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
        self.lang_states = {}
        self._render_lang_states()

        def progress(state, code, detail=""):
            self.lang_status(code, state, detail)
            if state in ("ok", "fail"):
                self.log(f"{'✅' if state == 'ok' else '❌'} {lang_display(code)} {detail}")

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
                    targets = [v for v in (eng.extract_video_id(link) for link in links) if v]
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
                        eng.localize_metadata_via_llm(metadata, langs, parts, progress=progress)
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

    # ---------- playlists tab ----------

    def build_playlists(self, tab):
        frame = ctk.CTkFrame(tab, fg_color="transparent")
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

    def build_schedule(self, tab):
        frame = ctk.CTkFrame(tab, fg_color="transparent")
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
                status.configure(text=g("sched_bad_date"), text_color=COLOR_RETRY)
                return
            if eng.set_publishAt(self.youtube, video_id, publish_datetime):
                status.configure(text=g("sched_done").format(
                    date=publish_datetime.strftime("%d.%m.%Y %H:%M")), text_color=COLOR_OK)
        ctk.CTkButton(frame, text=g("sched_set"), font=FONT, command=schedule).pack(anchor="w")

    # ---------- settings tab ----------

    def build_settings(self, tab):
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(expand=True, fill="both")

        def rerender():
            self.open_tab("settings", rebuild=True)

        ctk.CTkLabel(frame, text=g("set_language"), font=FONT_SMALL).pack(anchor="w")
        names = [GUI_STRINGS[c]["lang_name"] for c in LANG_CODES]
        codes = {GUI_STRINGS[c]["lang_name"]: c for c in LANG_CODES}
        lang_menu = ctk.CTkOptionMenu(frame, values=names, font=FONT_SMALL,
                                      command=lambda v: (self.switch_language(codes[v]),
                                                         self.refresh_after_language_change()))
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
            self.update_texts()
            rerender()
        ctk.CTkButton(frame, text=g("save"), font=FONT, command=save_common).pack(anchor="w")

        # --- API providers ---
        ctk.CTkLabel(frame, text=g("api_title"),
                     font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(20, 8))
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

            def edit(p=provider):
                self._provider_editor(tab, reg, p)
            ctk.CTkButton(row, text="✎", width=40, command=edit).pack(side="right", padx=2)

            def activate(p=provider):
                reg["active"] = p["id"]
                eng.save_provider_registry(reg)
                rerender()
            ctk.CTkButton(row, text="●", width=40, command=activate).pack(side="right", padx=2)

            def remove(p=provider):
                reg["providers"].remove(p)
                if reg.get("active") == p["id"] and reg["providers"]:
                    reg["active"] = reg["providers"][0]["id"]
                if reg.get("backup") == p["id"]:
                    reg["backup"] = None
                eng.save_provider_registry(reg)
                rerender()
            ctk.CTkButton(row, text="✕", width=40, fg_color="#7f1d1d",
                          command=remove).pack(side="right", padx=2)

        def add_provider():
            self._provider_editor(tab, reg, None)
        ctk.CTkButton(frame, text="＋ " + g("api_add"), font=FONT,
                      command=add_provider).pack(anchor="w", pady=(8, 0))

        # --- language presets ---
        ctk.CTkLabel(frame, text=g("presets_title"),
                     font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(20, 6))
        preset_row = ctk.CTkFrame(frame, fg_color="transparent")
        preset_row.pack(fill="x")
        presets = eng._ui.setdefault("language_presets", {})

        def apply_preset(value):
            codes = presets.get(value, [])
            if codes:
                self.profile["languages"] = sorted(codes)
                eng.save_channel_profiles(eng.load_channel_profiles())
                self.rebuild_tab("translate")
        preset_menu = ctk.CTkOptionMenu(preset_row, values=list(presets) or ["—"],
                                        command=apply_preset, font=FONT_SMALL, width=220)
        preset_menu.set(list(presets)[0] if presets else "—")
        preset_menu.pack(side="left", padx=(0, 8))

        def save_preset():
            top = ctk.CTkToplevel(self)
            top.title(g("preset_name_prompt"))
            top.geometry("420x200")
            top.grab_set()
            ctk.CTkLabel(top, text=g("preset_name_prompt"), font=FONT).pack(pady=(24, 4))
            entry = ctk.CTkEntry(top, width=280, font=FONT)
            entry.pack(pady=8)
            entry.focus_set()

            def apply_name():
                name = entry.get().strip()
                if not name:
                    return
                presets[name] = list(eng.get_profile_languages(self.profile))
                eng.save_ui_settings()
                top.destroy()
                self.rebuild_tab("settings")
            ctk.CTkButton(top, text=g("save"), font=FONT, command=apply_name).pack()
            entry.bind("<Return>", lambda e: apply_name())
        ctk.CTkButton(preset_row, text=g("preset_save"), font=FONT_SMALL,
                      command=save_preset).pack(side="left", padx=(0, 8))

        def delete_preset():
            value = preset_menu.get()
            if value in presets:
                del presets[value]
                eng.save_ui_settings()
                self.rebuild_tab("settings")
        ctk.CTkButton(preset_row, text=g("preset_delete"), font=FONT_SMALL, width=40,
                      fg_color="#7f1d1d", command=delete_preset).pack(side="left")
        if not presets:
            ctk.CTkLabel(frame, text=g("preset_none"), font=FONT_SMALL).pack(anchor="w")

        # --- translation languages (searchable, grows with the window) ---
        ctk.CTkLabel(frame, text=g("set_languages"),
                     font=FONT_TITLE).pack(anchor="w", pady=(20, 6))
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(frame, placeholder_text=g("lang_search"), font=FONT_SMALL)
        search_entry.pack(fill="x", pady=(0, 6))
        langs_frame = ctk.CTkFrame(frame, fg_color="transparent")
        langs_frame.pack(expand=True, fill="both", pady=(0, 8))

        def toggle_lang(c, v):
            langs = set(eng.get_profile_languages(self.profile))
            if v.get():
                langs.add(c)
            else:
                langs.discard(c)
            self.profile["languages"] = sorted(langs)
            eng.save_channel_profiles(eng.load_channel_profiles())
            self.rebuild_tab("translate")

        def build_languages_grid(query=""):
            catalog = eng.available_language_catalog()
            current_langs = set(eng.get_profile_languages(self.profile))
            query_l = query.strip().lower()
            codes = [c for c in sorted(catalog)
                     if not query_l
                     or query_l in c.lower()
                     or query_l in catalog[c].lower()
                     or query_l in lang_display(c).lower()]
            grid = ctk.CTkScrollableFrame(langs_frame, fg_color="transparent")
            grid.pack(expand=True, fill="both")
            for index, code in enumerate(codes):
                var = ctk.BooleanVar(value=code in current_langs)
                cb = ctk.CTkCheckBox(grid, text=f"{code} — {lang_display(code)}",
                                     variable=var,
                                     command=lambda c=code, v=var: toggle_lang(c, v),
                                     font=FONT_SMALL)
                cb.grid(row=index // 3, column=index % 3, sticky="w", padx=4, pady=2)
            for column in range(3):
                grid.grid_columnconfigure(column, weight=1)

        def on_search(*_):
            build_languages_grid(search_var.get())
        search_entry.bind("<KeyRelease>", on_search)
        build_languages_grid()


    def _provider_editor(self, tab, reg, provider):
        """Inline add/edit form for one API provider (replaces the provider list)."""
        for widget in tab.winfo_children():
            widget.destroy()
        is_new = provider is None

        def rerender():
            self.open_tab("settings")

        ctk.CTkLabel(tab, text=g("provider_new_title") if is_new
                     else g("provider_edit_title").format(name=provider.get("name", "")),
                     font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(tab, text=g("api_kind"), font=FONT_SMALL).pack(anchor="w")
        kind = ctk.StringVar(value=g("api_online") if (is_new or provider.get("auth"))
                             else g("api_local"))
        ctk.CTkSegmentedButton(tab, values=[g("api_online"), g("api_local")],
                               variable=kind, font=FONT_SMALL).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(tab, text=g("api_name"), font=FONT_SMALL).pack(anchor="w")
        name_entry = ctk.CTkEntry(tab, font=FONT_SMALL)
        if not is_new:
            name_entry.insert(0, provider.get("name", ""))
        name_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(tab, text=g("api_base"), font=FONT_SMALL).pack(anchor="w")
        base_entry = ctk.CTkEntry(tab, font=FONT_SMALL)
        base_entry.insert(0, "" if is_new else provider.get("base_url", ""))
        base_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(tab, text=g("api_keys"), font=FONT_SMALL).pack(anchor="w")
        keys_box = ctk.CTkTextbox(tab, height=70, font=FONT_SMALL)
        if not is_new and provider.get("api_keys"):
            keys_box.insert("1.0", ", ".join(provider["api_keys"]))
        keys_box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(tab, text=g("api_model"), font=FONT_SMALL).pack(anchor="w")
        model_row = ctk.CTkFrame(tab, fg_color="transparent")
        model_row.pack(fill="x", pady=(0, 10))
        model_entry = ctk.CTkEntry(model_row, font=FONT_SMALL)
        model_entry.pack(side="left", expand=True, fill="x", padx=(0, 8))
        if not is_new:
            model_entry.insert(0, provider.get("model", "auto"))

        def fetch_models():
            models = eng.fetch_local_models(base_entry.get().strip())
            if not models:
                status.configure(text=g("api_no_models"), text_color=COLOR_RETRY)
                return

            def set_model(value):
                model_entry.delete(0, "end")
                model_entry.insert(0, value)
            menu = ctk.CTkOptionMenu(model_row, values=models, font=FONT_SMALL,
                                     command=set_model)
            menu.set(models[0])
            menu.pack(side="left")
        ctk.CTkButton(model_row, text=g("api_fetch_models"), font=FONT_SMALL,
                      command=fetch_models).pack(side="left")

        status = ctk.CTkLabel(tab, text="", font=FONT_SMALL)
        status.pack(pady=6)

        def save():
            name = name_entry.get().strip()
            base = base_entry.get().strip()
            online = kind.get() == g("api_online")
            keys = [key.strip() for key in re.split(r"[,\s]+",
                                                    keys_box.get("1.0", "end").strip())
                    if key.strip()]
            model = model_entry.get().strip() or "auto"
            if not name:
                status.configure(text=g("api_name"), text_color=COLOR_RETRY)
                return
            if online and not base:
                status.configure(text=g("api_need_url"), text_color=COLOR_RETRY)
                return
            if online and not keys:
                status.configure(text=g("api_keys"), text_color=COLOR_RETRY)
                return
            entry = {
                "id": provider["id"] if not is_new else
                      eng.profile_slug(name, {p["id"] for p in reg["providers"]}),
                "name": name, "kind": "openai", "auth": online,
                "base_url": base, "api_keys": keys, "model": model,
            }
            if is_new:
                reg["providers"].append(entry)
                reg.setdefault("active", entry["id"])
            else:
                provider.update(entry)
            eng.save_provider_registry(reg)
            rerender()
        ctk.CTkButton(tab, text=g("save"), font=FONT, command=save).pack(anchor="w")
        ctk.CTkButton(tab, text=g("cancel"), font=FONT, fg_color="gray40",
                      command=rerender).pack(anchor="w", pady=6)


def main():
    try:
        saved = eng.load_json_file(eng.UI_SETTINGS_FILE)
        if saved.get("ui_language") in eng.STRINGS:
            eng._ui["language"] = saved["ui_language"]
        eng._ui["user_name"] = str(saved.get("user_name", "")).strip()
        eng._ui["ask_playlists"] = bool(saved.get("ask_playlists", True))
        eng._ui["ask_schedule"] = bool(saved.get("ask_schedule", True))
        eng._ui["language_presets"] = saved.get("language_presets", {})
        for key in ("ui_tr_mode", "ui_tr_type", "ui_tr_source", "ui_tr_parts",
                    "ui_add_defaults", "ui_sched", "ui_sched_date"):
            if key in saved:
                eng._ui[key] = saved[key]
    except (FileNotFoundError, ValueError):
        pass
    if not eng._ui["language"] or not eng._ui["user_name"]:
        eng._ui["language"] = None  # force the in-app onboarding screens
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
