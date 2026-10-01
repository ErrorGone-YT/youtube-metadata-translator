"""YouTube Metadata Translator — cross-platform CLI client.

Restructuring branch: new localized UI (en/uk/ru) with first-run onboarding.
The translation engine (LLM providers, YouTube operations) is fully present
but the menu items that use it are enabled in later phases.
"""

import os
import json
import re
import sys
import time
import html
import pickle
import random
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests
from googleapiclient.errors import HttpError
import isodate
import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
DEFAULT_CLIENT_SECRETS_FILE = "client_secrets.json"
UI_SETTINGS_FILE = "ui_settings.json"
CHANNEL_PROFILES_FILE = "channel_profiles.json"
METADATA_FILE = "metadata.json"
LOCALIZATIONS_FILE = "localizations.json"
DEFAULT_PUBLISH_TIME = "10:00"
GEMINI_API_FILE = "gemini_api.json"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_BASE_URL = "https://ollama.com/v1"
DEFAULT_OLLAMA_MODEL = "gemma4:31b"
OLLAMA_API_FILE = "ollama_api.json"
DEFAULT_CODECRAFT_BASE_URL = "https://codecraftapi.com/v1"
DEFAULT_CODECRAFT_MODEL = "deepseek-v4-flash-0731"
CODECRAFT_API_FILE = "codecraft_api.json"
SERIES_NAMES_FILE = "series_names.json"
ALLOWED_DAYS = ["Monday", "Wednesday", "Friday", "Sunday"]

GITHUB_BASE = "https://github.com/ErrorGone-YT/youtube-metadata-translator"
# READMEs live on the working branch until merged; switch to "main" after the merge.
REPO_BRANCH = "Restructuring"
GUIDE_LINKS = {
    "en": f"{GITHUB_BASE}/blob/{REPO_BRANCH}/README.md",
    "uk": f"{GITHUB_BASE}/blob/{REPO_BRANCH}/README.uk.md",
    "ru": f"{GITHUB_BASE}/blob/{REPO_BRANCH}/README.ru.md",
}
GOOGLE_CONSOLE_LINK = "https://console.cloud.google.com/apis/credentials"

# ---------------------------------------------------------------------------
# Localized interface strings
# ---------------------------------------------------------------------------

STRINGS = {
    "en": {
        "lang_select_title": "Choose the interface language / Виберіть мову інтерфейсу / Выберите язык интерфейса:",
        "ask_name": "How should I address you?",
        "menu_greeting": "Welcome, {name}! What are we doing?",
        "menu_translation": "Translation",
        "menu_playlist": "Add to playlist",
        "menu_schedule": "Scheduled publishing",
        "menu_settings": "Settings",
        "menu_exit": "Exit",
        "menu_choice": "Your choice: ",
        "coming_soon": "🚧 This feature is being polished and will appear soon.",
        "press_enter": "Press Enter to continue...",
        "invalid_choice": "❌ Invalid choice.",
        "setup_not_finished": (
            "⚡ Setup is not finished yet, so only Settings is available.\n"
            "   Open Settings: choose translation languages and add a translator API key."
        ),
        "secrets_missing_title": "❗ No client_secrets file found — the script can't reach YouTube yet.",
        "secrets_missing_steps": (
            "Short version:\n"
            "1) Open Google Cloud Console and create a project.\n"
            "2) Enable YouTube Data API v3 for it.\n"
            "3) Configure the OAuth consent screen and add your email to Test users.\n"
            "4) Create an OAuth client ID of type 'Desktop app' and download the JSON."
        ),
        "secrets_link_guide": "📖 Full step-by-step guide: {url}",
        "secrets_link_console": "🔑 Create the keys here: {url}",
        "secrets_retry": "Save the file as client_secrets.json into the data/ folder and press Enter (or type 0 to skip for now): ",
        "auth_opening_browser": "🌐 A browser window will open — sign in to the Google account of the channel.",
        "auth_success": "✅ Authorization successful: {channel}",
        "auth_failed": "❌ Authorization failed: {error}",
        "profile_wizard_title": "— Creating a channel profile —",
        "profile_name_prompt": "Profile name (anything you like): ",
        "profile_name_empty": "The name cannot be empty.",
        "profile_secrets_auto": "🔑 Secrets file found: {file}",
        "profile_secrets_pick": "Which secrets file is yours?",
        "profile_playlist_prompt": "Playlist ID to add videos to (Enter to skip): ",
        "profile_created": "✅ Profile '{name}' created.",
        "profile_pick_title": "Your channel profiles:",
        "profile_pick_add": "N) Add a channel",
        "profile_pick_prompt": "Profile number: ",
        "settings_title": "⚙️ Settings — {channel}",
        "settings_title_no_channel": "⚙️ Settings",
        "set_language": "Interface language",
        "set_name": "How to address you",
        "settings_interface": "Interface",
        "settings_translations": "Translations",
        "settings_playlists": "Playlists",
        "playlists_title": "▶️ Playlists — {channel}",
        "playlist_current": "Current playlist ID: {id}",
        "playlist_none": "No playlist set — videos are not added to any playlist.",
        "playlist_edit": "Set playlist ID",
        "playlist_prompt": "Playlist ID (the part after list= in the link; '-' — clear): ",
        "playlist_saved": "✅ Saved.",
        "schedule_title": "⏰ Scheduled publishing — {channel}",
        "schedule_note": "Videos go live on these weekdays at the local times below.",
        "schedule_time_prompt": "New local time (HH:MM, Enter — keep): ",
        "schedule_bad_time": "❌ Doesn't look like a HH:MM time.",
        "schedule_saved": "✅ {day}: {time}",
        "set_languages": "Translation languages",
        "set_parallel": "Number of parallel translations",
        "back": "Back",
        "name_saved": "✅ Got it, {name}!",
        "languages_screen_title": "🌍 Translation languages — {channel}",
        "languages_selected": "Selected ({n}): {list}",
        "languages_none": "No languages selected: the translation item will have nothing to do.",
        "languages_menu": "1) Toggle languages from the list\n2) Add a language by code (e.g. pt-BR)\n3) Clear selection\n0) Back",
        "languages_list_title": "Languages (x = selected):",
        "languages_toggle_hint": "Numbers separated by comma or space — toggle, A — select all, N — clear all, 0 — done",
        "languages_toggle_prompt": "Selection: ",
        "languages_keys_hint": "↑/↓ move · Space toggle · A/Ф select all · N/Т clear all · Enter done",
        "languages_didnt_understand": "❌ Didn't understand the selection.",
        "languages_add_prompt": "Language code (es, pt-BR, zh-Hans): ",
        "languages_bad_code": "❌ Doesn't look like a language code.",
        "languages_already": "This language is already selected.",
        "languages_clear_confirm": "Unselect all languages? (yes/no): ",
        "parallel_current": "🧵 Parallel translations now: {n}",
        "parallel_keys_found": "Found {n} API keys — that's how many translations can run at once.",
        "parallel_local_note": "For a local LM Studio more than 2 parallel translations rarely helps.",
        "parallel_prompt": "New value (Enter to keep {n}, auto = one per key): ",
        "parallel_saved_auto": "✅ Auto mode: one translation per API key ({n} now).",
        "parallel_not_positive": "❌ Enter a positive number.",
        "parallel_over_warning": "⚠️ More than {n} won't speed things up: extra threads will just wait in line.",
        "parallel_over_confirm": "Set anyway? (yes/no): ",
        "parallel_saved": "✅ Saved: {n} parallel translations.",
    },
    "uk": {
        "lang_select_title": "Choose the interface language / Виберіть мову інтерфейсу / Выберите язык интерфейса:",
        "ask_name": "Як до вас звертатися?",
        "menu_greeting": "Вітаю, {name}! Що робитимемо?",
        "menu_translation": "Переклад",
        "menu_playlist": "Додати до плейлиста",
        "menu_schedule": "Відкладена публікація",
        "menu_settings": "Налаштування",
        "menu_exit": "Вихід",
        "menu_choice": "Ваш вибір: ",
        "coming_soon": "🚧 Ця функція на підході — з'явиться незабаром.",
        "press_enter": "Натисніть Enter, щоб продовжити...",
        "invalid_choice": "❌ Некоректний вибір.",
        "setup_not_finished": (
            "⚡ Налаштування ще не завершено, тому доступні лише Налаштування.\n"
            "   Відкрийте їх: виберіть мови перекладу та додайте API-ключ перекладача."
        ),
        "secrets_missing_title": "❗ Не знайдено файл client_secrets — скрипт поки не має доступу до YouTube.",
        "secrets_missing_steps": (
            "Коротко:\n"
            "1) Відкрийте Google Cloud Console і створіть проєкт.\n"
            "2) Увімкніть для нього YouTube Data API v3.\n"
            "3) Налаштуйте екран згоди OAuth і додайте свою пошту до Test users.\n"
            "4) Створіть OAuth client ID типу 'Desktop app' і завантажте JSON."
        ),
        "secrets_link_guide": "📖 Повна покрокова інструкція: {url}",
        "secrets_link_console": "🔑 Створити ключі тут: {url}",
        "secrets_retry": "Збережіть файл як client_secrets.json у папку data/ і натисніть Enter (або 0 — щоб пропустити поки що): ",
        "auth_opening_browser": "🌐 Відкриється вікно браузера — увійдіть у Google-акаунт каналу.",
        "auth_success": "✅ Авторизація успішна: {channel}",
        "auth_failed": "❌ Помилка авторизації: {error}",
        "profile_wizard_title": "— Створення профілю каналу —",
        "profile_name_prompt": "Назва профілю (яка завгодно): ",
        "profile_name_empty": "Назва не може бути порожньою.",
        "profile_secrets_auto": "🔑 Знайдено файл ключів: {file}",
        "profile_secrets_pick": "Котрий з файлів ключів ваш?",
        "profile_playlist_prompt": "ID плейлиста для додавання відео (Enter — пропустити): ",
        "profile_created": "✅ Профіль '{name}' створено.",
        "profile_pick_title": "Ваші профілі каналів:",
        "profile_pick_add": "N) Додати канал",
        "profile_pick_prompt": "Номер профілю: ",
        "settings_title": "⚙️ Налаштування — {channel}",
        "settings_title_no_channel": "⚙️ Налаштування",
        "set_language": "Мова інтерфейсу",
        "set_name": "Як до вас звертатися",
        "settings_interface": "Інтерфейс",
        "settings_translations": "Переклади",
        "settings_playlists": "Плейлисти",
        "playlists_title": "▶️ Плейлисти — {channel}",
        "playlist_current": "Поточний ID плейлиста: {id}",
        "playlist_none": "Плейлист не задано — відео нікуди не додаються.",
        "playlist_edit": "Задати ID плейлиста",
        "playlist_prompt": "ID плейлиста (частина після list= у посиланні; '-' — прибрати): ",
        "playlist_saved": "✅ Збережено.",
        "schedule_title": "⏰ Відкладена публікація — {channel}",
        "schedule_note": "Відео виходять у ці дні тижня о вказаний локальний час.",
        "schedule_time_prompt": "Новий локальний час (HH:MM, Enter — залишити): ",
        "schedule_bad_time": "❌ Не схоже на час HH:MM.",
        "schedule_saved": "✅ {day}: {time}",
        "set_languages": "Мови перекладу",
        "set_parallel": "Кількість одночасних перекладів",
        "back": "Назад",
        "name_saved": "✅ Домовилися, {name}!",
        "languages_screen_title": "🌍 Мови перекладу — {channel}",
        "languages_selected": "Вибрано ({n}): {list}",
        "languages_none": "Мови не вибрано: пункту перекладу буде нічого робити.",
        "languages_menu": "1) Позначити мови у списку\n2) Додати мову за кодом (наприклад pt-BR)\n3) Очистити вибір\n0) Назад",
        "languages_list_title": "Мови (x = вибрано):",
        "languages_toggle_hint": "Номери через кому або пробіл — перемкнути, A — вибрати всі, N — зняти всі, 0 — готово",
        "languages_toggle_prompt": "Вибір: ",
        "languages_keys_hint": "↑/↓ рух · Пробіл — вибрати/зняти · A/Ф — вибрати всі · N/Т — зняти всі · Enter — готово",
        "languages_didnt_understand": "❌ Не зрозумів вибір.",
        "languages_add_prompt": "Код мови (es, pt-BR, zh-Hans): ",
        "languages_bad_code": "❌ Не схоже на мовний код.",
        "languages_already": "Ця мова вже вибрана.",
        "languages_clear_confirm": "Зняти всі мови? (так/ні): ",
        "parallel_current": "🧵 Одночасних перекладів зараз: {n}",
        "parallel_keys_found": "Знайдено {n} API-ключів — стільки перекладів можна вести одночасно.",
        "parallel_local_note": "Для локального LM Studio більше 2 одночасних перекладів рідко допомагає.",
        "parallel_prompt": "Нове значення (Enter — залишити {n}, auto = за кількістю ключів): ",
        "parallel_saved_auto": "✅ Авто-режим: один переклад на кожен ключ (зараз {n}).",
        "parallel_not_positive": "❌ Введіть додатне число.",
        "parallel_over_warning": "⚠️ Більше ніж {n} не прискорить: зайві потоки просто чекатимуть черги.",
        "parallel_over_confirm": "Усе одно встановити? (так/ні): ",
        "parallel_saved": "✅ Збережено: {n} одночасних перекладів.",
    },
    "ru": {
        "lang_select_title": "Choose the interface language / Виберіть мову інтерфейсу / Выберите язык интерфейса:",
        "ask_name": "Как к вам обращаться?",
        "menu_greeting": "Приветствую, {name}! Что будем делать?",
        "menu_translation": "Перевод",
        "menu_playlist": "Добавить в плейлист",
        "menu_schedule": "Отложенная публикация",
        "menu_settings": "Настройки",
        "menu_exit": "Выход",
        "menu_choice": "Ваш выбор: ",
        "coming_soon": "🚧 Эта функция в разработке и появится скоро.",
        "press_enter": "Нажмите Enter, чтобы продолжить...",
        "invalid_choice": "❌ Некорректный выбор.",
        "setup_not_finished": (
            "⚡ Настройка ещё не завершена, поэтому доступен только пункт Настройки.\n"
            "   Откройте его: выберите языки перевода и добавьте API-ключ переводчика."
        ),
        "secrets_missing_title": "❗ Не найден файл client_secrets — скрипт пока не имеет доступа к YouTube.",
        "secrets_missing_steps": (
            "Коротко:\n"
            "1) Открой Google Cloud Console и создай проект.\n"
            "2) Включи для него YouTube Data API v3.\n"
            "3) Настрой экран согласования OAuth и добавь свою почту в Test users.\n"
            "4) Создай OAuth client ID типа 'Desktop app' и скачай JSON."
        ),
        "secrets_link_guide": "📖 Полная пошаговая инструкция: {url}",
        "secrets_link_console": "🔑 Создать ключи здесь: {url}",
        "secrets_retry": "Сохрани файл как client_secrets.json в папку data/ и нажми Enter (или 0 — чтобы пропустить пока): ",
        "auth_opening_browser": "🌐 Откроется окно браузера — войди в Google-аккаунт канала.",
        "auth_success": "✅ Авторизация успешна: {channel}",
        "auth_failed": "❌ Ошибка авторизации: {error}",
        "profile_wizard_title": "— Создание профиля канала —",
        "profile_name_prompt": "Название профиля (какое угодно): ",
        "profile_name_empty": "Название не может быть пустым.",
        "profile_secrets_auto": "🔑 Найден файл ключей: {file}",
        "profile_secrets_pick": "Который из файлов ключей твой?",
        "profile_playlist_prompt": "ID плейлиста для добавления видео (Enter — пропустить): ",
        "profile_created": "✅ Профиль '{name}' создан.",
        "profile_pick_title": "Твои профили каналов:",
        "profile_pick_add": "N) Добавить канал",
        "profile_pick_prompt": "Номер профиля: ",
        "settings_title": "⚙️ Настройки — {channel}",
        "settings_title_no_channel": "⚙️ Настройки",
        "set_language": "Язык интерфейса",
        "set_name": "Как к тебе обращаться",
        "settings_interface": "Интерфейс",
        "settings_translations": "Переводы",
        "settings_playlists": "Плейлисты",
        "playlists_title": "▶️ Плейлисты — {channel}",
        "playlist_current": "Текущий ID плейлиста: {id}",
        "playlist_none": "Плейлист не задан — видео никуда не добавляются.",
        "playlist_edit": "Задать ID плейлиста",
        "playlist_prompt": "ID плейлиста (часть после list= в ссылке; '-' — убрать): ",
        "playlist_saved": "✅ Сохранено.",
        "schedule_title": "⏰ Отложенная публикация — {channel}",
        "schedule_note": "Видео выходят в эти дни недели в указанное локальное время.",
        "schedule_time_prompt": "Новое локальное время (HH:MM, Enter — оставить): ",
        "schedule_bad_time": "❌ Не похоже на время HH:MM.",
        "schedule_saved": "✅ {day}: {time}",
        "set_languages": "Языки перевода",
        "set_parallel": "Количество одновременных переводов",
        "back": "Назад",
        "name_saved": "✅ Договорились, {name}!",
        "languages_screen_title": "🌍 Языки перевода — {channel}",
        "languages_selected": "Выбрано ({n}): {list}",
        "languages_none": "Языки не выбраны: пункту перевода будет нечего делать.",
        "languages_menu": "1) Отметить языки в списке\n2) Добавить язык по коду (например pt-BR)\n3) Очистить выбор\n0) Назад",
        "languages_list_title": "Языки (x = выбрано):",
        "languages_toggle_hint": "Номера через запятую или пробел — переключить, A — выбрать все, N — снять все, 0 — готово",
        "languages_toggle_prompt": "Выбор: ",
        "languages_keys_hint": "↑/↓ движение · Пробел — выбрать/снять · A/Ф — выбрать все · N/Т — снять все · Enter — готово",
        "languages_didnt_understand": "❌ Не понял выбор.",
        "languages_add_prompt": "Код языка (es, pt-BR, zh-Hans): ",
        "languages_bad_code": "❌ Не похоже на языковой код.",
        "languages_already": "Этот язык уже выбран.",
        "languages_clear_confirm": "Снять все языки? (да/нет): ",
        "parallel_current": "🧵 Одновременных переводов сейчас: {n}",
        "parallel_keys_found": "Найдено {n} API-ключей — столько переводов можно вести одновременно.",
        "parallel_local_note": "Для локального LM Studio больше 2 одновременных переводов редко даёт выигрыш.",
        "parallel_prompt": "Новое значение (Enter — оставить {n}, auto = по числу ключей): ",
        "parallel_saved_auto": "✅ Авто-режим: один перевод на каждый ключ (сейчас {n}).",
        "parallel_not_positive": "❌ Введи положительное число.",
        "parallel_over_warning": "⚠️ Больше {n} не ускорит: лишние потоки просто будут ждать очереди.",
        "parallel_over_confirm": "Всё равно установить? (да/нет): ",
        "parallel_saved": "✅ Сохранено: {n} одновременных переводов.",
    },
}

_ui = {"language": None, "user_name": ""}


def t(key, **kwargs):
    """Localized string with graceful fallback to English."""
    text = STRINGS.get(_ui["language"], STRINGS["en"]).get(key) or STRINGS["en"].get(key)
    if text is None:
        return key
    return text.format(**kwargs) if kwargs else text


def confirm(prompt):
    """Yes in all three interface languages."""
    return input(prompt).strip().lower() in ("y", "yes", "1", "д", "да", "т", "так")


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def data_file_path(filename):
    """Resolve a profile file under data/ and reject paths outside that folder."""
    full_path = os.path.abspath(os.path.join(DATA_DIR, filename))
    data_path = os.path.abspath(DATA_DIR)
    if os.path.commonpath([full_path, data_path]) != data_path:
        raise ValueError(f"Profile file must be inside {DATA_DIR}: {filename}")
    return full_path


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def load_json_file(filename):
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(filename, data):
    full_path = os.path.join(DATA_DIR, filename)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_ui_settings():
    if not _ui["language"]:
        choose_ui_language()
    if not _ui["user_name"]:
        ask_user_name()
    save_ui_settings()


def save_ui_settings():
    save_json_file(UI_SETTINGS_FILE, {"ui_language": _ui["language"], "user_name": _ui["user_name"]})


def restore_ui_settings():
    """Load saved language/name before anything is printed; returns True if onboarding is needed."""
    try:
        saved = load_json_file(UI_SETTINGS_FILE)
        if saved.get("ui_language") in STRINGS:
            _ui["language"] = saved["ui_language"]
        _ui["user_name"] = str(saved.get("user_name", "")).strip()
    except (FileNotFoundError, ValueError):
        pass
    needs_onboarding = False
    if not _ui["language"]:
        choose_ui_language()
        needs_onboarding = True
    if not _ui["user_name"]:
        ask_user_name()
        needs_onboarding = True
    if needs_onboarding:
        save_ui_settings()
    return needs_onboarding


def choose_ui_language():
    """Ask for the interface language; shown before any other localized text."""
    while True:
        print(t("lang_select_title"))
        print("1) English\n2) Українська\n3) Русский")
        choice = input("> ").strip()
        if choice == "1":
            _ui["language"] = "en"
        elif choice == "2":
            _ui["language"] = "uk"
        elif choice == "3":
            _ui["language"] = "ru"
        else:
            continue
        clear_console()
        return _ui["language"]


def ask_user_name():
    while True:
        name = input(t("ask_name") + " ").strip()
        if name:
            _ui["user_name"] = name
            clear_console()
            print(t("name_saved").format(name=name))
            return name


# ---------------------------------------------------------------------------
# Google authorization and YouTube operations (engine — menu wiring comes later)
# ---------------------------------------------------------------------------


def authenticate(profile):
    full_token_path = data_file_path(profile["token_file"])
    full_secrets_path = data_file_path(profile["client_secrets_file"])

    credentials = None
    if os.path.exists(full_token_path):
        with open(full_token_path, "rb") as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            if not os.path.exists(full_secrets_path):
                raise FileNotFoundError(f"Client secrets file not found: {full_secrets_path}")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                full_secrets_path, SCOPES)
            credentials = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(full_token_path), exist_ok=True)
        with open(full_token_path, "wb") as token:
            pickle.dump(credentials, token)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)


def refresh_profile_identity(youtube, profile, profiles):
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    if not response.get("items"):
        raise RuntimeError("The authorized Google account has no YouTube channel.")
    channel = response["items"][0]
    profile["channel_id"] = channel["id"]
    profile["channel_title"] = channel["snippet"]["title"]
    save_channel_profiles(profiles)
    add_series_name(channel["snippet"]["title"])


def set_publishAt(youtube, video_id, publish_datetime):
    try:
        # One call: privacyStatus=private + publishAt together, 50 quota units.
        youtube.videos().update(
            part="status",
            body={
                "id": video_id,
                "status": {
                    "privacyStatus": "private",
                    "publishAt": publish_datetime.isoformat("T") + "Z",
                },
            },
        ).execute()
        print(f"✅ {video_id}: {publish_datetime.strftime('%Y-%m-%d %H:%M UTC')}")
        return True
    except Exception as e:
        print(f"set_publishAt error: {e}")
        return False


def calendar_publish_time(publ_calendar, day_name):
    times = publ_calendar.get(day_name) or []
    return times[0] if times else DEFAULT_PUBLISH_TIME


def local_to_utc(publish_datetime):
    """Shift naive local wall-clock time to naive UTC using the current DST-aware offset."""
    return publish_datetime - datetime.now().astimezone().utcoffset()


def to_publish_datetime(publish_date, publ_calendar):
    publish_time = calendar_publish_time(publ_calendar, publish_date.strftime("%A"))
    publish_datetime = datetime.strptime(
        f"{publish_date.strftime('%Y-%m-%d')} {publish_time}", "%Y-%m-%d %H:%M"
    )
    return local_to_utc(publish_datetime), publish_time


def translate_day(day_name):
    """Localized weekday name for display; comparison always uses English names."""
    days = {
        "en": ["Monday", "Wednesday", "Friday", "Sunday"],
        "uk": ["Понеділок", "Середа", "П'ятниця", "Неділя"],
        "ru": ["Понедельник", "Среда", "Пятница", "Воскресенье"],
    }
    names = days.get(_ui["language"], days["en"])
    return dict(zip(ALLOWED_DAYS, names)).get(day_name, day_name)


def next_allowed_date(start_date, days_ahead, allowed_days):
    current_date = start_date + timedelta(days=days_ahead)
    while current_date.strftime("%A") not in allowed_days:
        current_date += timedelta(days=1)
    return current_date


def get_channel_videos(youtube):
    """Uploads playlist entries for normal (non-live) videos, with their durations."""
    videos = []
    next_page_token = None
    response = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    while True:
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()
        videos.extend(playlist_response["items"])
        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token:
            break

    filtered = []
    durations = {}
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in videos]
    found_ids = set()
    live_ids = set()
    # videos().list accepts up to 50 ids per call; batching saves a lot of quota.
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]
        details = youtube.videos().list(
            part="snippet,contentDetails", id=",".join(batch)
        ).execute()
        for video in details.get("items", []):
            found_ids.add(video["id"])
            durations[video["id"]] = isodate.parse_duration(
                video["contentDetails"]["duration"]
            ).total_seconds()
            live_status = video["snippet"].get("liveBroadcastContent", "none")
            if live_status in ["live", "upcoming"]:
                live_ids.add(video["id"])
    for item in videos:
        video_id = item["snippet"]["resourceId"]["videoId"]
        if video_id in found_ids and video_id not in live_ids:
            filtered.append(item)
    return filtered, durations


def update_video_metadata(youtube, video_id, title, description, localizations):
    response = youtube.videos().list(part="snippet,localizations", id=video_id).execute()
    if not response["items"]:
        print(f"Video {video_id} not found")
        return False

    video = response["items"][0]
    body = {
        "id": video_id,
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": video["snippet"].get("tags", []),
            "categoryId": video["snippet"]["categoryId"],
            "defaultLanguage": "en",
        },
    }

    merged_localizations = video.get("localizations", {}).copy()
    if localizations:
        for lang_code, texts in localizations.items():
            merged_localizations[lang_code] = {
                "title": texts["title"][:100],
                "description": texts["description"][:5000],
            }
        body["localizations"] = merged_localizations

    youtube.videos().update(part="snippet,localizations", body=body).execute()
    return True


def add_video_to_playlist(youtube, video_id, playlist_id):
    if not playlist_id:
        return
    existing = youtube.playlistItems().list(
        part="snippet", playlistId=playlist_id, videoId=video_id, maxResults=1
    ).execute()
    if existing.get("items"):
        return
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()


def extract_video_id(url):
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"embed\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def normalize_description(text):
    """Decode copied HTML and keep paragraph breaks as normal newline characters."""
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n[ \t]+\n", "\n\n", text)
    return text.strip()


def get_description_from_dialog():
    """Open a multiline field so a browser description can be pasted as-is."""
    try:
        import tkinter
        from tkinter import messagebox, scrolledtext

        root = tkinter.Tk()
        root.title("Description")
        root.geometry("760x700")
        root.minsize(760, 700)

        tkinter.Label(
            root,
            text="Paste the full description below (Ctrl+V), then press Continue.",
            anchor="w", padx=12, pady=10,
        ).pack(fill="x")
        field = scrolledtext.ScrolledText(root, wrap="word", font=("Segoe UI", 11))
        field.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        result = {"text": None}

        def paste_from_clipboard(event=None):
            try:
                text = root.clipboard_get()
            except tkinter.TclError:
                messagebox.showerror("Clipboard", "Could not read the clipboard.", parent=root)
                return "break"
            field.insert("insert", text)
            field.focus_set()
            return "break"

        def confirm():
            result["text"] = field.get("1.0", "end-1c")
            root.destroy()

        buttons = tkinter.Frame(root)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        tkinter.Button(buttons, text="Continue", command=confirm).pack(side="right")
        tkinter.Button(buttons, text="Paste", command=paste_from_clipboard).pack(side="left")
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        field.bind("<Control-v>", paste_from_clipboard)
        field.bind("<Control-V>", paste_from_clipboard)
        field.focus_set()
        root.mainloop()

        if result["text"] is None:
            raise RuntimeError("Description entry was cancelled.")
        return result["text"]
    except Exception as error:
        raise RuntimeError(f"Could not enter the description: {error}") from error


# ---------------------------------------------------------------------------
# LLM translation engine (all providers)
# ---------------------------------------------------------------------------


def load_local_llm_config():
    try:
        return load_json_file("local_llm.json")
    except FileNotFoundError:
        return {"temperature": 0.25, "max_tokens": 2400, "timeout_seconds": 180}


def load_gemini_api_keys():
    if not os.path.exists(data_file_path(GEMINI_API_FILE)):
        raise FileNotFoundError(
            f'No data/{GEMINI_API_FILE}. Create it: {{"GEMINI_API_KEY": "key1, key2"}}'
        )
    raw = load_json_file(GEMINI_API_FILE).get("GEMINI_API_KEY", "")
    keys = [key.strip() for key in re.split(r"[,\s]+", str(raw)) if key.strip()]
    if not keys:
        raise ValueError(f"{GEMINI_API_FILE} has no GEMINI_API_KEY.")
    return keys


def load_ollama_api_keys():
    if not os.path.exists(data_file_path(OLLAMA_API_FILE)):
        raise FileNotFoundError(
            f'No data/{OLLAMA_API_FILE}. Create it: {{"OLLAMA_API_KEY": "key1, key2"}}'
        )
    raw = load_json_file(OLLAMA_API_FILE).get("OLLAMA_API_KEY", "")
    keys = [key.strip() for key in re.split(r"[,\s]+", str(raw)) if key.strip()]
    if not keys:
        raise ValueError(f"{OLLAMA_API_FILE} has no OLLAMA_API_KEY.")
    return keys


def load_codecraft_api_keys():
    if not os.path.exists(data_file_path(CODECRAFT_API_FILE)):
        raise FileNotFoundError(
            f'No data/{CODECRAFT_API_FILE}. Create it: {{"CODECRAFT_API_KEY": "cc_key1, cc_key2"}}'
        )
    raw = load_json_file(CODECRAFT_API_FILE).get("CODECRAFT_API_KEY", "")
    keys = [key.strip() for key in re.split(r"[,\s]+", str(raw)) if key.strip()]
    if not keys:
        raise ValueError(f"{CODECRAFT_API_FILE} has no CODECRAFT_API_KEY.")
    return keys


def resolve_llm_provider(config):
    """Explicit 'provider' wins; otherwise detect by which key file exists."""
    provider = str(config.get("provider", "")).lower()
    if provider in ("gemini", "lmstudio", "ollama", "codecraft"):
        return provider
    for provider_name, key_file in (
        ("codecraft", CODECRAFT_API_FILE),
        ("ollama", OLLAMA_API_FILE),
        ("gemini", GEMINI_API_FILE),
    ):
        try:
            if os.path.exists(data_file_path(key_file)):
                return provider_name
        except ValueError:
            pass
    return "lmstudio"


def translator_ready(config=None):
    """True when a cloud translation key is available (LM Studio alone doesn't count)."""
    try:
        config = config or load_local_llm_config()
        return resolve_llm_provider(config) != "lmstudio"
    except (FileNotFoundError, ValueError):
        return False


_gemini_key_lock = threading.Lock()
_gemini_key_offset = 0
_gemini_dead_keys = set()


def parse_retry_hint(message):
    match = re.search(r"retry in ([\d.]+)\s*(ms|s|minutes?)", message, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "ms":
        seconds = value / 1000
    elif unit.startswith("min"):
        seconds = value * 60
    else:
        seconds = value
    return max(1, int(seconds) + 1)


def gemini_http_error(response):
    try:
        detail = response.json().get("error", {}).get("message", "")
    except ValueError:
        detail = ""
    return f"Gemini HTTP {response.status_code}: {detail or response.text[:300]}"


def request_gemini_completion(prompt, system_prompt, config):
    """One generateContent call against the Gemini API; keys round-robin."""
    global _gemini_key_offset
    all_keys = load_gemini_api_keys()
    keys = [key for key in all_keys if key not in _gemini_dead_keys] or all_keys
    with _gemini_key_lock:
        start = _gemini_key_offset % len(keys)
        _gemini_key_offset += 1
    model = config.get("gemini_model", DEFAULT_GEMINI_MODEL)
    is_gemma = model.startswith("gemma")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    generation_config = {
        "temperature": config.get("temperature", 0.25),
        "maxOutputTokens": config.get("gemini_max_output_tokens", 8192),
        "responseMimeType": "application/json",
        "responseSchema": {
            "type": "OBJECT",
            "required": ["title", "description"],
            "properties": {
                "title": {"type": "STRING"},
                "description": {"type": "STRING"},
            },
        },
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }
    if is_gemma:
        # Gemma rejects systemInstruction (500) and thinkingBudget (400).
        payload["contents"][0]["parts"][0]["text"] = f"{system_prompt}\n\n{prompt}"
    else:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}

    last_404 = None
    for offset in range(len(keys)):
        key = keys[(start + offset) % len(keys)]
        for patience in range(5):
            try:
                response = requests.post(
                    url, json=payload,
                    headers={"x-goog-api-key": key},
                    timeout=config.get("timeout_seconds", 180),
                )
            except requests.Timeout:
                if patience == 4:
                    raise
                time.sleep(5)
                continue
            if response.status_code not in (500, 503) or patience == 4:
                break
            time.sleep(5 + random.uniform(0, 3))
        if response.status_code == 404:
            last_404 = gemini_http_error(response)
            if key not in _gemini_dead_keys:
                _gemini_dead_keys.add(key)
                live_left = len([k for k in all_keys if k not in _gemini_dead_keys])
                print(f"⚠️ Key #{all_keys.index(key) + 1} can't see {model}. Keys left: {live_left}.")
            continue
        if response.status_code != 200:
            raise RuntimeError(gemini_http_error(response))
        data = response.json()
        candidates = data.get("candidates") or [{}]
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            raise ValueError(f"Gemini empty answer (finishReason={candidates[0].get('finishReason')})")
        return text
    raise RuntimeError(f"{last_404} — no key of {len(all_keys)} sees model {model}.")


_ollama_key_lock = threading.Lock()
_ollama_key_offset = 0


def request_ollama_completion(prompt, system_prompt, config):
    """Ollama cloud chat completion; keys round-robin, dead keys skipped."""
    global _ollama_key_offset
    keys = load_ollama_api_keys()
    with _ollama_key_lock:
        start = _ollama_key_offset % len(keys)
        _ollama_key_offset += 1
    endpoint = config.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model = config.get("ollama_model", DEFAULT_OLLAMA_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.get("temperature", 0.25),
        "max_tokens": config.get("max_tokens", 2400),
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    last_error = None
    for offset in range(len(keys)):
        key = keys[(start + offset) % len(keys)]
        response = requests.post(
            f"{endpoint}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=config.get("timeout_seconds", 180),
        )
        if response.status_code in (401, 403, 404) and offset < len(keys) - 1:
            last_error = f"Ollama HTTP {response.status_code}: {response.text[:200]}"
            continue
        if response.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {response.status_code}: {response.text[:300]}")
        answer = response.json()
        content = answer.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise ValueError(f"Ollama empty answer: {str(answer)[:200]}")
        return content
    raise RuntimeError(f"{last_error} — none of {len(keys)} Ollama keys worked.")


_codecraft_key_lock = threading.Lock()
_codecraft_key_offset = 0


def request_codecraft_completion(prompt, system_prompt, config):
    """CodeCraft chat completion; keys round-robin, dead keys skipped."""
    global _codecraft_key_offset
    keys = load_codecraft_api_keys()
    with _codecraft_key_lock:
        start = _codecraft_key_offset % len(keys)
        _codecraft_key_offset += 1
    endpoint = config.get("codecraft_base_url", DEFAULT_CODECRAFT_BASE_URL).rstrip("/")
    model = config.get("codecraft_model", DEFAULT_CODECRAFT_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.get("temperature", 0.25),
        # Reasoning tokens count toward max_tokens — a tight cap leaves content empty.
        "max_tokens": config.get("codecraft_max_tokens", 8192),
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    last_error = None
    for offset in range(len(keys)):
        key = keys[(start + offset) % len(keys)]
        response = requests.post(
            f"{endpoint}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=config.get("timeout_seconds", 180),
        )
        if response.status_code in (401, 403) and offset < len(keys) - 1:
            last_error = f"CodeCraft HTTP {response.status_code}: {response.text[:200]}"
            continue
        if response.status_code != 200:
            message = f"CodeCraft HTTP {response.status_code}: {response.text[:300]}"
            retry_after = response.headers.get("Retry-After", "")
            if response.status_code == 429 and retry_after:
                message += f" (retry in {retry_after}s)"
            raise RuntimeError(message)
        answer = response.json()
        choice = answer.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content")
        if not content:
            raise ValueError(
                f"CodeCraft empty answer (finish_reason={choice.get('finish_reason')}): {str(answer)[:150]}"
            )
        return content
    raise RuntimeError(f"{last_error} — none of {len(keys)} CodeCraft keys worked.")


def get_local_llm_model(config):
    model = config.get("model", "auto")
    if model != "auto":
        return model
    endpoint = config["base_url"].rstrip("/")
    response = requests.get(f"{endpoint}/models", timeout=10)
    response.raise_for_status()
    models = response.json().get("data", [])
    if not models:
        raise RuntimeError("LM Studio is reachable, but no model is loaded.")
    return models[0]["id"]


def request_lmstudio_completion(endpoint, model, prompt, system_prompt, config):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.get("temperature", 0.25),
        "max_tokens": config.get("max_tokens", 2400),
        "stream": False,
    }
    response = requests.post(
        f"{endpoint}/chat/completions", json=payload,
        timeout=config.get("timeout_seconds", 180),
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_llm_json(content):
    """Accept plain JSON and recover JSON wrapped in a code block or with trailing chatter."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        content = content.rsplit("```", 1)[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        value, _ = json.JSONDecoder().raw_decode(content)
        return value


def load_series_names():
    if not os.path.exists(data_file_path(SERIES_NAMES_FILE)):
        return []
    names = load_json_file(SERIES_NAMES_FILE)
    if not isinstance(names, list):
        raise ValueError(f"{SERIES_NAMES_FILE} must contain a list of names.")
    return [str(name).strip() for name in names if str(name).strip()]


def add_series_name(name):
    name = (name or "").strip()
    if not name:
        return
    names = load_series_names()
    if any(name.casefold() == existing.casefold() for existing in names):
        return
    names.append(name)
    save_json_file(SERIES_NAMES_FILE, names)


def remove_unrequested_series_lines(description, source_description):
    """Drop LLM-invented series footer lines absent from the source description."""
    series_names = load_series_names()
    if not series_names:
        return description
    source_casefold = source_description.casefold()
    kept = []
    for line in description.split("\n"):
        invented = any(
            name.casefold() in line.casefold() and name.casefold() not in source_casefold
            for name in series_names
        )
        if not invented:
            kept.append(line)
    return "\n".join(kept).strip()


def restore_source_line_breaks(description, source_description):
    """Rebuild the source's line breaks: models often double single newlines."""
    out_content = [line.strip() for line in description.split("\n") if line.strip()]
    src_content = [line.strip() for line in source_description.split("\n") if line.strip()]
    if not out_content or len(out_content) != len(src_content):
        return description
    rebuilt = []
    out_index = 0
    for line in source_description.split("\n"):
        if not line.strip():
            if rebuilt and rebuilt[-1] != "":
                rebuilt.append("")
            continue
        rebuilt.append(out_content[out_index])
        out_index += 1
    return "\n".join(rebuilt).rstrip()


def clean_existing_series_footers(localizations, source_description):
    changed = False
    for localized_metadata in localizations.values():
        description = localized_metadata.get("description")
        if not isinstance(description, str):
            continue
        cleaned = remove_unrequested_series_lines(description, source_description)
        if cleaned != description:
            localized_metadata["description"] = cleaned
            changed = True
    return changed


def localize_language_via_llm(provider, endpoint, model, config, language_code,
                              language_name, source_title, source_description):
    """Localize metadata for one language; raises after the final retry fails."""
    max_attempts = max(1, config.get("retry_attempts", 6 if provider in ("gemini", "codecraft") else 3))
    system_prompt = "You are a precise multilingual YouTube metadata localizer."
    series_names = load_series_names()
    series_rule = ""
    if series_names:
        names_list = ", ".join(f'"{name}"' for name in series_names)
        series_rule = (
            f" Never add a line containing {names_list} "
            "unless that exact name appears in the source description."
        )
    prompt = f"""Localize the YouTube metadata below for {language_name} ({language_code}).

This is adaptive localization, not a literal translation. Preserve the scene, calm magical tone, calls to action, links, emojis, and line breaks. Use natural wording a native speaker would use. Keep Hogwarts as the locally conventional name if one exists. Do not invent facts, keywords, claims, sections, series labels, or footers.{series_rule}

Return ONLY the JSON object required by the schema.
- title: at most 100 characters, compelling and natural for YouTube.
- description: at most 5000 characters; preserve the source structure and URL exactly.
- line breaks: copy the source exactly — "\\n" for each source line break and "\\n\\n" only where the source has a blank line; never insert extra blank lines.

SOURCE TITLE:
{source_title}

SOURCE DESCRIPTION:
{source_description}"""
    for attempt in range(1, max_attempts + 1):
        try:
            if provider == "gemini":
                content = request_gemini_completion(prompt, system_prompt, config)
            elif provider == "ollama":
                content = request_ollama_completion(prompt, system_prompt, config)
            elif provider == "codecraft":
                content = request_codecraft_completion(prompt, system_prompt, config)
            else:
                content = request_lmstudio_completion(endpoint, model, prompt, system_prompt, config)
            answer = parse_llm_json(content)
            title = answer["title"].strip()
            description = remove_unrequested_series_lines(
                answer["description"].strip(), source_description
            )
            description = restore_source_line_breaks(description, source_description)
            if not title or not description:
                raise ValueError("the model returned an empty title or description")
            if len(title) > 100 or len(description) > 5000:
                raise ValueError(f"limits exceeded: title={len(title)}, description={len(description)}")
            return {"title": title, "description": description}
        except Exception as error:
            if attempt == max_attempts:
                raise
            message = str(error)
            wait_seconds = parse_retry_hint(message)
            if wait_seconds is None:
                if "429" in message:
                    wait_seconds = 20
                elif "500" in message or "503" in message:
                    wait_seconds = 10
                else:
                    wait_seconds = 2
            print(f"RETRY {language_code} ({attempt}/{max_attempts - 1}), waiting {wait_seconds}s: "
                  f"{message.splitlines()[0]}")
            time.sleep(wait_seconds)


def localize_metadata_via_llm(metadata, target_languages=None):
    """Create localized titles and descriptions via the resolved provider."""
    config = load_local_llm_config()
    provider = resolve_llm_provider(config)
    endpoint = config.get("base_url", "http://localhost:1234/v1").rstrip("/")
    if provider == "gemini":
        model = config.get("gemini_model", DEFAULT_GEMINI_MODEL)
    elif provider == "ollama":
        endpoint = config.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        model = config.get("ollama_model", DEFAULT_OLLAMA_MODEL)
    elif provider == "codecraft":
        endpoint = config.get("codecraft_base_url", DEFAULT_CODECRAFT_BASE_URL).rstrip("/")
        model = config.get("codecraft_model", DEFAULT_CODECRAFT_MODEL)
    else:
        model = get_local_llm_model(config)
    source_title = metadata.get("title", "").strip()
    source_description = metadata.get("description", "").strip()
    if not source_title or not source_description:
        raise ValueError("metadata must contain a non-empty title and description.")

    if target_languages is None:
        target_languages = []
    target_languages = list(dict.fromkeys(target_languages))
    language_names = config.get("language_names", {})
    translated = {}
    errors = []

    for language_code in target_languages:
        if language_code == "en":
            translated[language_code] = {
                "title": source_title,
                "description": source_description,
            }

    queued = [code for code in target_languages if code != "en"]
    if queued:
        max_workers = min(len(queued), resolve_parallelism(config))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            def delayed(idx, code):
                # Stagger starts so all threads don't slam the model at once.
                time.sleep(idx * 1.5)
                return localize_language_via_llm(
                    provider, endpoint, model, config,
                    code, language_names.get(code, code), source_title, source_description,
                )
            futures = {pool.submit(delayed, idx, code): code for idx, code in enumerate(queued)}
            for future in as_completed(futures):
                language_code = futures[future]
                try:
                    translated[language_code] = future.result()
                    result = translated[language_code]
                    print(f"OK {language_code}: title {len(result['title'])}, description {len(result['description'])}")
                except Exception as error:
                    errors.append(f"{language_code}: {error}")
                    print(f"FAILED {language_code}: {error}")

    if errors:
        raise RuntimeError("Localization failed for some languages:\n" + "\n".join(errors))

    ordered = {code: translated[code] for code in target_languages if code in translated}
    save_json_file(LOCALIZATIONS_FILE, ordered)
    return ordered


def fetch_video_source_metadata(youtube, video_id):
    response = youtube.videos().list(part="snippet", id=video_id).execute()
    if not response.get("items"):
        raise ValueError(f"Video {video_id} not found.")
    snippet = response["items"][0]["snippet"]
    metadata = {
        "title": (snippet.get("title") or "").strip(),
        "description": normalize_description(snippet.get("description") or ""),
    }
    if not metadata["title"] or not metadata["description"]:
        raise ValueError(f"Video {video_id} has an empty title or description.")
    return metadata


# ---------------------------------------------------------------------------
# Channel profiles
# ---------------------------------------------------------------------------


def load_channel_profiles():
    try:
        profiles = load_json_file(CHANNEL_PROFILES_FILE)
    except FileNotFoundError:
        profiles = {"profiles": []}
        save_json_file(CHANNEL_PROFILES_FILE, profiles)
        return profiles
    if not isinstance(profiles, dict) or not isinstance(profiles.get("profiles"), list):
        raise ValueError("channel_profiles.json must contain a 'profiles' list.")
    return profiles


def save_channel_profiles(profiles):
    save_json_file(CHANNEL_PROFILES_FILE, profiles)


def migrate_profile_paths(profile):
    """Move per-profile files into profiles/<profile_id>/ (pre-folder layout kept at data/ root)."""
    migrated = False
    for key, new_name in (("token_file", "token.pickle"), ("publ_calendar_file", "calendar.json")):
        new_rel = f"profiles/{profile['profile_id']}/{new_name}"
        old_rel = profile.get(key, "")
        if old_rel == new_rel:
            continue
        old_abs = os.path.join(DATA_DIR, old_rel)
        new_abs = os.path.join(DATA_DIR, new_rel)
        if os.path.isfile(old_abs):
            os.makedirs(os.path.dirname(new_abs), exist_ok=True)
            shutil.move(old_abs, new_abs)
            # Drop the legacy folder if the move left it empty (e.g. tokens/).
            old_dir = os.path.dirname(old_abs)
            if os.path.normpath(old_dir) != os.path.normpath(DATA_DIR) and not os.listdir(old_dir):
                os.rmdir(old_dir)
        profile[key] = new_rel
        migrated = True
    return migrated


def get_profile_languages(profile):
    languages = profile.get("languages")
    if isinstance(languages, list):
        return [str(code) for code in languages]
    return []


def valid_language_code(code):
    return bool(re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?", code))


def available_language_catalog():
    catalog = {
        "en": "English", "es": "Spanish", "pt": "Portuguese", "hi": "Hindi",
        "id": "Indonesian", "it": "Italian", "ja": "Japanese", "ko": "Korean",
        "de": "German", "fr": "French", "ru": "Russian", "ar": "Arabic",
        "tr": "Turkish", "vi": "Vietnamese", "pl": "Polish", "nl": "Dutch",
        "uk": "Ukrainian",
    }
    try:
        catalog.update(load_local_llm_config().get("language_names", {}))
    except (FileNotFoundError, ValueError):
        pass
    return catalog


def profile_slug(display_name, existing_ids):
    base = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_") or "channel"
    candidate = base
    number = 2
    while candidate in existing_ids:
        candidate = f"{base}_{number}"
        number += 1
    return candidate


def find_secrets_files():
    """All client_secrets*.json files in data/ (any name the user chose)."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        f for f in os.listdir(DATA_DIR)
        if f.startswith("client_secrets") and f.endswith(".json")
    )


def create_profile_wizard(profiles, secrets_files):
    clear_console()
    print(t("profile_wizard_title"))
    name = ""
    while not name:
        name = input(t("profile_name_prompt")).strip()
        if not name:
            print(t("profile_name_empty"))

    if len(secrets_files) == 1:
        secrets_file = secrets_files[0]
        print(t("profile_secrets_auto").format(file=secrets_file))
    else:
        print(t("profile_secrets_pick"))
        for index, filename in enumerate(secrets_files, start=1):
            print(f"  {index}) {filename}")
        while True:
            choice = input(t("menu_choice")).strip()
            if choice.isdigit() and 1 <= int(choice) <= len(secrets_files):
                secrets_file = secrets_files[int(choice) - 1]
                break

    # The playlist is configured later in Settings — asking here confuses new users.
    existing_ids = {p["profile_id"] for p in profiles["profiles"]}
    profile_id = profile_slug(name, existing_ids)
    # Everything a profile owns lives in its own subfolder: profiles/<profile_id>/
    token_file = f"profiles/{profile_id}/token.pickle"
    calendar_file = f"profiles/{profile_id}/calendar.json"
    save_json_file(calendar_file, {})

    profile = {
        "profile_id": profile_id,
        "display_name": name,
        "channel_id": "",
        "channel_title": "",
        "token_file": token_file,
        "client_secrets_file": secrets_file,
        "playlist_id": "",
        "publ_calendar_file": calendar_file,
    }
    profiles["profiles"].append(profile)
    save_channel_profiles(profiles)
    print(t("profile_created").format(name=name))
    return profile


def select_profile(profiles):
    secrets_files = find_secrets_files()
    while True:
        clear_console()
        print(t("profile_pick_title"))
        for index, profile in enumerate(profiles["profiles"], start=1):
            name = profile.get("channel_title") or profile.get("display_name")
            token_exists = os.path.exists(data_file_path(profile["token_file"]))
            status = "✅" if token_exists else "🔑"
            print(f"{index}) {name} ({status})")
        print(t("profile_pick_add"))
        choice = input(t("profile_pick_prompt")).strip().lower()
        if choice == "0":
            return None
        if choice == "n":
            if not secrets_files:
                ensure_secrets()
                secrets_files = find_secrets_files()
                if not secrets_files:
                    continue
            return create_profile_wizard(profiles, secrets_files)
        if choice.isdigit() and 1 <= int(choice) <= len(profiles["profiles"]):
            return profiles["profiles"][int(choice) - 1]
        print(t("invalid_choice"))


def ensure_secrets():
    """Loop until a client_secrets file appears; localized instructions with links."""
    while True:
        secrets = find_secrets_files()
        if secrets:
            return secrets
        clear_console()
        print(f"{t('secrets_missing_title')}\n")
        print(t("secrets_missing_steps"))
        print()
        print(t("secrets_link_guide").format(url=GUIDE_LINKS.get(_ui["language"], GUIDE_LINKS["en"])))
        print(t("secrets_link_console").format(url=GOOGLE_CONSOLE_LINK))
        answer = input(f"\n{t('secrets_retry')}").strip().lower()
        if answer in ("0", "s", "skip", "x", "н", "х"):
            return []


def manage_profile_languages(profile, profiles):
    """Settings screen for the languages this profile translates."""
    while True:
        selected = get_profile_languages(profile)
        channel_name = profile.get("channel_title") or profile.get("display_name")
        clear_console()
        print(t("languages_screen_title").format(channel=channel_name))
        if selected:
            print(t("languages_selected").format(n=len(selected), list=", ".join(selected)))
        else:
            print(t("languages_none"))
        print(t("languages_menu"))
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice == "1":
            profile["languages"] = choose_languages_from_catalog(selected)
        elif choice == "2":
            code = input(t("languages_add_prompt")).strip()
            if not valid_language_code(code):
                print(t("languages_bad_code"))
                continue
            if code in selected:
                print(t("languages_already"))
                continue
            selected.append(code)
            profile["languages"] = selected
        elif choice == "3":
            if confirm(t("languages_clear_confirm")):
                profile["languages"] = []
            else:
                continue
        else:
            print(t("invalid_choice"))
            continue
        save_channel_profiles(profiles)


def _enable_ansi_windows():
    """Enable ANSI escape codes in the classic Windows console."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _read_key():
    """One keypress: 'up', 'down', 'space', 'enter', or the lowercase character."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            return {"H": "up", "P": "down"}.get(ch2, "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch == " ":
            return "space"
        return ch.lower()
    import termios
    import tty
    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = ch + sys.stdin.read(2)
            return {"\x1b[A": "up", "\x1b[B": "down"}.get(seq, "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch == " ":
            return "space"
        return ch.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)


def choose_languages_from_catalog(selected):
    """Toggle-menu over the language catalog; returns the new selection.

    Interactive checkbox list (arrows + space) in a real terminal; the
    numbered-input mode stays as a fallback for non-interactive terminals.
    """
    catalog = available_language_catalog()
    codes = sorted(catalog) + [code for code in selected if code not in catalog]
    working = list(selected)

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return _choose_languages_by_number(codes, catalog, working)

    _enable_ansi_windows()
    cursor = 0

    def render(first=False):
        if not first:
            # Jump back above the list and clear it for a flicker-free redraw.
            sys.stdout.write("\x1b[%dA\x1b[J" % (len(codes) + 1))
        lines = []
        for index, code in enumerate(codes):
            arrow = "❯" if index == cursor else " "
            mark = "x" if code in working else " "
            lines.append(f"{arrow} [{mark}] {index + 1}) {code} — {catalog.get(code, code)}")
        lines.append(t("languages_keys_hint"))
        print("\n".join(lines), flush=True)

    print(t("languages_list_title"))
    sys.stdout.write("\x1b[?25l")  # hide the cursor while the list is live
    try:
        render(first=True)
        while True:
            key = _read_key()
            if key == "up":
                cursor = (cursor - 1) % len(codes)
            elif key == "down":
                cursor = (cursor + 1) % len(codes)
            elif key == "space":
                code = codes[cursor]
                if code in working:
                    working.remove(code)
                else:
                    working.append(code)
            elif key in ("a", "а", "ф"):
                working = list(codes)
            elif key in ("n", "н", "т"):
                working = []
            elif key in ("enter", "0", "q"):
                break
            render()
    finally:
        sys.stdout.write("\x1b[?25h")  # show the cursor back
        print()
    return working


def _choose_languages_by_number(codes, catalog, working):
    """Numbered-input fallback for terminals without raw key access."""
    while True:
        clear_console()
        print(t("languages_list_title"))
        for index, code in enumerate(codes, start=1):
            mark = "x" if code in working else " "
            print(f"  [{mark}] {index}) {code} — {catalog.get(code, code)}")
        print(f"\n{t('languages_toggle_hint')}")
        answer = input(t("languages_toggle_prompt")).strip().lower()
        if answer == "0":
            return working
        if answer in ("a", "а", "ф"):
            working = list(codes)
            continue
        if answer in ("n", "н", "т"):
            working = []
            continue
        toggled = False
        for token in re.split(r"[,\s]+", answer):
            if token.isdigit() and 1 <= int(token) <= len(codes):
                code = codes[int(token) - 1]
                if code in working:
                    working.remove(code)
                else:
                    working.append(code)
                toggled = True
        if not toggled:
            print(t("languages_didnt_understand"))


def suggested_parallelism(config):
    """How many translations can safely run at once: one per cloud API key."""
    provider = resolve_llm_provider(config)
    key_counts = {
        "gemini": load_gemini_api_keys,
        "ollama": load_ollama_api_keys,
        "codecraft": load_codecraft_api_keys,
    }
    loader = key_counts.get(provider)
    if loader:
        try:
            return max(1, len(loader()))
        except (FileNotFoundError, ValueError):
            return 1
    return 2


def resolve_parallelism(config):
    """'auto' (or anything unparsable) = one thread per cloud API key."""
    value = config.get("max_parallel_languages", "auto")
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return max(1, suggested_parallelism(config))


def manage_parallelism_setting():
    config = load_local_llm_config()
    suggested = suggested_parallelism(config)
    raw_current = config.get("max_parallel_languages", "auto")
    current_display = "auto" if str(raw_current).lower() == "auto" else raw_current
    provider = resolve_llm_provider(config)
    print(f"\n{t('parallel_current').format(n=current_display)}")
    if provider in ("gemini", "ollama", "codecraft"):
        print(t("parallel_keys_found").format(n=suggested))
    else:
        print(t("parallel_local_note"))
    answer = input(t("parallel_prompt").format(n=current_display)).strip().lower()
    if not answer:
        return
    if answer in ("auto", "аuto", "а", "a"):
        config["max_parallel_languages"] = "auto"
        save_json_file("local_llm.json", config)
        print(t("parallel_saved_auto").format(n=suggested))
        return
    if not answer.isdigit() or int(answer) < 1:
        print(t("parallel_not_positive"))
        return
    value = int(answer)
    if value > suggested:
        print(t("parallel_over_warning").format(n=suggested))
        if not confirm(t("parallel_over_confirm")):
            return
    config["max_parallel_languages"] = value
    save_json_file("local_llm.json", config)
    print(t("parallel_saved").format(n=value))


def interface_menu():
    while True:
        clear_console()
        print(f"\n{t('settings_interface')}")
        print(f"1) {t('set_language')}")
        print(f"2) {t('set_name')}")
        print(f"0) {t('back')}")
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice == "1":
            choose_ui_language()
            save_ui_settings()
        elif choice == "2":
            ask_user_name()
            save_ui_settings()
        else:
            print(t("invalid_choice"))


def translations_menu(profile, profiles):
    while True:
        clear_console()
        print(f"\n{t('settings_translations')}")
        print(f"1) {t('set_languages')}")
        print(f"2) {t('set_parallel')}")
        print(f"0) {t('back')}")
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice == "1":
            manage_profile_languages(profile, profiles)
        elif choice == "2":
            manage_parallelism_setting()
        else:
            print(t("invalid_choice"))


def playlists_menu(profile, profiles):
    while True:
        clear_console()
        channel = profile.get("channel_title") or profile.get("display_name")
        print(f"\n{t('playlists_title').format(channel=channel)}")
        playlist_id = profile.get("playlist_id", "")
        if playlist_id:
            print(t("playlist_current").format(id=playlist_id))
        else:
            print(t("playlist_none"))
        print(f"\n1) {t('playlist_edit')}")
        print(f"0) {t('back')}")
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice == "1":
            answer = input(t("playlist_prompt")).strip()
            if not answer:
                continue
            if answer == "-":
                answer = ""
            profile["playlist_id"] = answer
            save_channel_profiles(profiles)
            print(t("playlist_saved"))
        else:
            print(t("invalid_choice"))


def schedule_menu(profile, profiles):
    """Per-profile publishing calendar: a local time for each allowed weekday."""
    while True:
        clear_console()
        channel = profile.get("channel_title") or profile.get("display_name")
        print(f"\n{t('schedule_title').format(channel=channel)}")
        print(t("schedule_note"))
        publ_calendar = load_json_file(profile["publ_calendar_file"])
        for index, day in enumerate(ALLOWED_DAYS, start=1):
            times = publ_calendar.get(day) or []
            day_time = times[0] if times else DEFAULT_PUBLISH_TIME
            print(f"{index}) {translate_day(day)} — {day_time}")
        print(f"0) {t('back')}")
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(ALLOWED_DAYS):
            day = ALLOWED_DAYS[int(choice) - 1]
            answer = input(t("schedule_time_prompt")).strip()
            if not answer:
                continue
            try:
                datetime.strptime(answer, "%H:%M")
            except ValueError:
                print(t("schedule_bad_time"))
                continue
            publ_calendar[day] = [answer]
            save_json_file(profile["publ_calendar_file"], publ_calendar)
            print(t("schedule_saved").format(day=translate_day(day), time=answer))
        else:
            print(t("invalid_choice"))


def settings_menu(profile, profiles):
    while True:
        clear_console()
        if profile and (profile.get("channel_title") or profile.get("display_name")):
            channel = profile.get("channel_title") or profile.get("display_name")
            print(f"\n{t('settings_title').format(channel=channel)}")
        else:
            print(f"\n{t('settings_title_no_channel')}")
        print(f"1) {t('settings_interface')}")
        if profile:
            print(f"2) {t('settings_translations')}")
            print(f"3) {t('settings_playlists')}")
            print(f"4) {t('menu_schedule')}")
        print(f"0) {t('back')}")
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice == "1":
            interface_menu()
        elif choice == "2" and profile:
            translations_menu(profile, profiles)
        elif choice == "3" and profile:
            playlists_menu(profile, profiles)
        elif choice == "4" and profile:
            schedule_menu(profile, profiles)
        else:
            print(t("invalid_choice"))


# ---------------------------------------------------------------------------
# Main menus
# ---------------------------------------------------------------------------


def profile_is_ready(profile):
    """A profile is configured once it has translation languages and a translator key."""
    return bool(profile) and bool(get_profile_languages(profile)) and translator_ready()


def profile_menu(profile, profiles):
    while True:
        clear_console()
        print(t("menu_greeting").format(name=_ui["user_name"]))
        ready = profile_is_ready(profile)
        if not ready:
            print(f"\n{t('setup_not_finished')}\n")
            print(f"1) {t('menu_settings')}")
            print(f"0) {t('menu_exit')}")
            choice = input(f"\n{t('menu_choice')}").strip()
            if choice == "0":
                return
            if choice == "1":
                settings_menu(profile, profiles)
            else:
                print(t("invalid_choice"))
            continue

        print(f"\n1) {t('menu_translation')}")
        print(f"2) {t('menu_playlist')}")
        print(f"3) {t('menu_schedule')}")
        print(f"4) {t('menu_settings')}")
        print(f"0) {t('menu_exit')}")
        choice = input(f"\n{t('menu_choice')}").strip()
        if choice == "0":
            return
        if choice in ("1", "2", "3"):
            # Engine is committed but the wiring lands in the next phases.
            print(f"\n{t('coming_soon')}")
            input(t("press_enter"))
        elif choice == "4":
            settings_menu(profile, profiles)
        else:
            print(t("invalid_choice"))


def main():
    restore_ui_settings()
    profiles = load_channel_profiles()
    for existing_profile in profiles["profiles"]:
        if migrate_profile_paths(existing_profile):
            save_channel_profiles(profiles)
    secrets_files = ensure_secrets()

    profile = None
    if profiles["profiles"]:
        profile = select_profile(profiles)
    elif secrets_files:
        profile = create_profile_wizard(profiles, secrets_files)

    if profile:
        try:
            print(t("auth_opening_browser"))
            youtube = authenticate(profile)
            refresh_profile_identity(youtube, profile, profiles)
            print(t("auth_success").format(channel=profile.get("channel_title")))
            time.sleep(1.5)  # a beat to read the success line, then straight to the menu
        except Exception as error:
            print(t("auth_failed").format(error=error))
            input(t("press_enter"))

    profile_menu(profile, profiles)


if __name__ == "__main__":
    main()
