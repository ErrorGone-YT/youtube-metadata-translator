import os
import pickle
import json
import re
import time
import html
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests
from datetime import datetime, timedelta 
from googleapiclient.errors import HttpError
import isodate
import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
DEFAULT_LANGUAGE_CODE = "en" 
CHANNEL_PROFILES_FILE = "channel_profiles.json"
DEFAULT_CLIENT_SECRETS_FILE = "client_secrets_translator.json"
DEFAULT_PUBL_CALENDAR_FILE = "publ_calendar.json"
DEFAULT_PUBLISH_TIME = "10:00"
METADATA_FILE = "metadata.json"
LOCALIZATIONS_FILE = "localizations.json"
GEMINI_API_FILE = "gemini_api.json"
DEFAULT_OLLAMA_BASE_URL = "https://ollama.com/v1"
DEFAULT_OLLAMA_MODEL = "gemma4:31b"
OLLAMA_API_FILE = "ollama_api.json"
DEFAULT_CODECRAFT_BASE_URL = "https://codecraftapi.com/v1"
DEFAULT_CODECRAFT_MODEL = "deepseek-v4-flash-0731"
CODECRAFT_API_FILE = "codecraft_api.json"
# gemini-2.5-flash is closed to new API keys ("no longer available to new
# users"); 3.8-flash answers on every key.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
SERIES_NAMES_FILE = "series_names.json"
DEFAULT_LANGUAGES = {
    "en": "English", "es": "Spanish", "pt": "Portuguese", "hi": "Hindi",
    "id": "Indonesian", "it": "Italian", "ja": "Japanese", "ko": "Korean",
    "de": "German", "fr": "French", "ru": "Russian", "ar": "Arabic",
    "tr": "Turkish", "vi": "Vietnamese", "pl": "Polish", "nl": "Dutch",
    "uk": "Ukrainian",
}


def data_file_path(filename):
    """Resolve a profile file under data/ and reject paths outside that folder."""
    full_path = os.path.abspath(os.path.join(DATA_DIR, filename))
    data_path = os.path.abspath(DATA_DIR)
    if os.path.commonpath([full_path, data_path]) != data_path:
        raise ValueError(f"Profile file must be inside {DATA_DIR}: {filename}")
    return full_path


def authenticate(profile):
    full_token_path = data_file_path(profile["token_file"])
    full_secrets_path = data_file_path(profile["client_secrets_file"])
    
    credentials = None
    if os.path.exists(full_token_path):
        with open(full_token_path, 'rb') as token:
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
        with open(full_token_path, 'wb') as token:
            pickle.dump(credentials, token)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)



def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def load_json_file(filename):
    full_path = os.path.join(DATA_DIR, filename)
    with open(full_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(filename, data):
    full_path = os.path.join(DATA_DIR, filename)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_channel_profiles():
    profile_path = data_file_path(CHANNEL_PROFILES_FILE)
    if not os.path.exists(profile_path):
        profiles = {"profiles": []}
        save_json_file(CHANNEL_PROFILES_FILE, profiles)
        return profiles

    profiles = load_json_file(CHANNEL_PROFILES_FILE)
    if not isinstance(profiles, dict) or not isinstance(profiles.get("profiles"), list):
        raise ValueError("channel_profiles.json must contain a 'profiles' list.")
    return profiles


def save_channel_profiles(profiles):
    save_json_file(CHANNEL_PROFILES_FILE, profiles)


def get_profile_languages(profile):
    """Language codes selected for this profile; falls back to previous localizations."""
    languages = profile.get("languages")
    if isinstance(languages, list):
        return [str(code) for code in languages]
    localizations_path = data_file_path("localizations.json")
    if os.path.exists(localizations_path):
        return list(load_json_file("localizations.json").keys())
    return []


def valid_language_code(code):
    return bool(re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?", code))


def available_language_catalog():
    """Union of the defaults, local_llm.json names and earlier localizations."""
    catalog = dict(DEFAULT_LANGUAGES)
    try:
        catalog.update(load_local_llm_config().get("language_names", {}))
    except (FileNotFoundError, ValueError):
        pass
    localizations_path = data_file_path("localizations.json")
    if os.path.exists(localizations_path):
        for code in load_json_file("localizations.json"):
            catalog.setdefault(code, code)
    return catalog


def choose_languages_from_catalog(selected):
    """Toggle-menu over the language catalog; returns the new selection."""
    catalog = available_language_catalog()
    codes = sorted(catalog) + [code for code in selected if code not in catalog]
    working = list(selected)
    while True:
        print("\nЯзыки (x = выбран):")
        for index, code in enumerate(codes, start=1):
            mark = "x" if code in working else " "
            print(f"  [{mark}] {index}) {code} — {catalog.get(code, 'добавлен вручную')}")
        print("\nНомера через запятую или пробел — переключить, A — выбрать все, N — снять все, 0 — готово")
        answer = input("Выбор: ").strip().lower()
        if answer == "0":
            return working
        if answer in ("a", "а"):
            working = list(codes)
            continue
        if answer in ("n", "н"):
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
            print("❌ Не понял выбор.")


def suggested_parallelism(config):
    """How many translations can safely run at once: one per cloud API key."""
    provider = resolve_llm_provider(config)
    if provider == "gemini":
        try:
            return max(1, len(load_gemini_api_keys()))
        except (FileNotFoundError, ValueError):
            return 1
    if provider == "ollama":
        try:
            return max(1, len(load_ollama_api_keys()))
        except (FileNotFoundError, ValueError):
            return 1
    if provider == "codecraft":
        try:
            return max(1, len(load_codecraft_api_keys()))
        except (FileNotFoundError, ValueError):
            return 1
    # LM Studio serves every thread from one local model; beyond 2 it barely helps.
    return 2


def manage_parallelism_setting():
    """Prompt for the global max_parallel_languages value in local_llm.json."""
    config = load_local_llm_config()
    current = int(config.get("max_parallel_languages", 5))
    suggested = suggested_parallelism(config)
    provider = resolve_llm_provider(config)
    print(f"\n🧵 Одновременных переводов сейчас: {current}")
    if provider in ("gemini", "ollama", "codecraft"):
        print(f"Найдено API-ключей: {suggested} — столько переводов можно вести одновременно.")
        print("Каждый ключ выдерживает ~5 запросов в минуту, скорость растёт вместе с числом ключей.")
    else:
        print("Для LM Studio больше 2 одновременных переводов обычно не даёт выигрыша.")
    answer = input(f"Новое значение (Enter — оставить {current}): ").strip()
    if not answer:
        print("Оставлено без изменений.")
        return
    if not answer.isdigit() or int(answer) < 1:
        print("❌ Нужно положительное число.")
        return
    value = int(answer)
    if value > suggested:
        print(f"⚠️ Больше {suggested} не ускорит: переводов будет не больше, чем ключей, "
              "лишние потоки будут ждать своей очереди.")
        if input("Всё равно установить? (да/нет): ").strip().lower() not in ("д", "да", "y", "yes"):
            return
    config["max_parallel_languages"] = value
    save_json_file("local_llm.json", config)
    print(f"✅ Сохранено: {value} одновременных переводов.")


def manage_profile_languages(profile, profiles):
    """Settings screen for the languages this profile translates."""
    while True:
        selected = get_profile_languages(profile)
        channel_name = profile.get("channel_title") or profile.get("display_name")
        parallelism = load_local_llm_config().get("max_parallel_languages", 5)
        print(f"\n⚙️ Языки перевода — {channel_name}")
        if selected:
            print(f"Выбрано ({len(selected)}): {', '.join(selected)}")
        else:
            print("Языки не выбраны: пункт 4 ничего переводить не будет.")
        print(f"Одновременных переводов: {parallelism}")
        print("""
1) Отметить языки в списке
2) Добавить язык по коду (например pt-BR)
3) Очистить выбор
4) Количество одновременных переводов (общая настройка)
0) Назад""")
        choice = input("\nВыбор: ").strip()
        if choice == "0":
            return
        if choice == "1":
            profile["languages"] = choose_languages_from_catalog(selected)
        elif choice == "2":
            code = input("Код языка (es, pt-BR, zh-Hans): ").strip()
            if not valid_language_code(code):
                print("❌ Не похож на языковой код.")
                continue
            if code in selected:
                print("Этот язык уже выбран.")
                continue
            selected.append(code)
            profile["languages"] = selected
        elif choice == "3":
            if input("Снять все языки? (да/нет): ").strip().lower() in ["д", "да", "y", "yes"]:
                profile["languages"] = []
            else:
                continue
        elif choice == "4":
            manage_parallelism_setting()
            continue
        else:
            print("❌ Некорректный выбор.")
            continue
        save_channel_profiles(profiles)


def profile_slug(display_name, existing_ids):
    base = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_") or "channel"
    candidate = base
    number = 2
    while candidate in existing_ids:
        candidate = f"{base}_{number}"
        number += 1
    return candidate


def create_channel_profile(profiles):
    display_name = input("Channel profile name: ").strip()
    if not display_name:
        raise ValueError("Profile name cannot be empty.")

    secrets_file = input(
        f"Client secrets filename [{DEFAULT_CLIENT_SECRETS_FILE}]: "
    ).strip() or DEFAULT_CLIENT_SECRETS_FILE
    data_file_path(secrets_file)
    if not os.path.exists(data_file_path(secrets_file)):
        raise FileNotFoundError(f"Client secrets file not found: data/{secrets_file}")

    playlist_id = input("Playlist ID for this channel (Enter to skip): ").strip()
    existing_ids = {profile["profile_id"] for profile in profiles["profiles"]}
    profile_id = profile_slug(display_name, existing_ids)
    calendar_file = f"publ_calendar_{profile_id}.json"
    if not os.path.exists(data_file_path(calendar_file)):
        if os.path.exists(data_file_path(DEFAULT_PUBL_CALENDAR_FILE)):
            save_json_file(calendar_file, load_json_file(DEFAULT_PUBL_CALENDAR_FILE))
        else:
            save_json_file(calendar_file, {})

    profile = {
        "profile_id": profile_id,
        "display_name": display_name,
        "channel_id": "",
        "channel_title": "",
        "token_file": f"tokens/{profile_id}.pickle",
        "client_secrets_file": secrets_file,
        "playlist_id": playlist_id,
        "publ_calendar_file": calendar_file,
    }
    profiles["profiles"].append(profile)
    save_channel_profiles(profiles)
    return profile


def select_channel_profile():
    profiles = load_channel_profiles()
    while True:
        if not profiles["profiles"]:
            print("\nПрофили каналов не найдены. Создадим новый.")
            try:
                return create_channel_profile(profiles), profiles
            except (ValueError, FileNotFoundError) as error:
                print(f"Профиль не создан: {error}")
                continue

        print("\nYouTube channel profiles:")
        for index, profile in enumerate(profiles["profiles"], start=1):
            name = profile.get("channel_title") or profile.get("display_name")
            token_exists = os.path.exists(data_file_path(profile["token_file"]))
            status = "authorized" if token_exists else "authorization required"
            print(f"{index}) {name} ({status})")
        print("N) Authorize a new channel")
        choice = input("Choose a profile: ").strip().lower()
        if choice == "n":
            try:
                return create_channel_profile(profiles), profiles
            except (ValueError, FileNotFoundError) as error:
                print(f"Profile was not created: {error}")
                continue
        if choice.isdigit() and 1 <= int(choice) <= len(profiles["profiles"]):
            return profiles["profiles"][int(choice) - 1], profiles
        print("Invalid choice.")


def refresh_profile_identity(youtube, profile, profiles):
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    if not response.get("items"):
        raise RuntimeError("The authorized Google account has no YouTube channel.")
    channel = response["items"][0]
    profile["channel_id"] = channel["id"]
    profile["channel_title"] = channel["snippet"]["title"]
    save_channel_profiles(profiles)
    add_series_name(channel["snippet"]["title"])


def extract_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def set_publishAt(youtube, video_id, publish_datetime):
    try:
        # One call: privacyStatus=private + publishAt together, 50 quota units
        # instead of the 100 a separate "set private first" round-trip cost.
        youtube.videos().update(
            part="status",
            body={
                "id": video_id,
                "status": {
                    "privacyStatus": "private",
                    "publishAt": publish_datetime.isoformat("T") + "Z"
                }
            }
        ).execute()
        print(f"✅ Отложенная публикация {video_id}: {publish_datetime.strftime('%Y-%m-%d %H:%M UTC')}")
        return True
    except Exception as e:
        print(f"Ошибка при установке publishAt: {e}")
        return False

def calendar_publish_time(publ_calendar, day_name):
    """Time from the publishing calendar, with a safe default for an empty entry."""
    times = publ_calendar.get(day_name) or []
    return times[0] if times else DEFAULT_PUBLISH_TIME


def local_to_utc(publish_datetime):
    """Shift naive local wall-clock time to naive UTC using the current DST-aware offset."""
    return publish_datetime - datetime.now().astimezone().utcoffset()


def to_publish_datetime(publish_date, publ_calendar):
    """Calendar date + scheduled time, shifted to UTC for YouTube publishAt."""
    publish_time = calendar_publish_time(publ_calendar, publish_date.strftime("%A"))
    publish_datetime = datetime.strptime(
        f"{publish_date.strftime('%Y-%m-%d')} {publish_time}",
        "%Y-%m-%d %H:%M"
    )
    return local_to_utc(publish_datetime), publish_time


def ask_publish_date(publ_calendar, allowed_days):
    """Prompt for a ddmmyy date on an allowed weekday; returns the UTC publish time."""
    while True:
        user_date = input("\n📅 Дата публикации (ddmmyy): ").strip()
        try:
            publish_date = datetime.strptime(user_date, "%d%m%y")
        except ValueError:
            print("❌ Некорректная дата!")
            continue
        day_name = publish_date.strftime("%A")
        if day_name not in allowed_days:
            print(f"❌ Публикация ТОЛЬКО в {', '.join(allowed_days)}!")
            continue
        publish_datetime, publish_time = to_publish_datetime(publish_date, publ_calendar)
        print(f"🕐 Выбрано время на {day_name}: {publish_time}")
        return publish_datetime


def ask_start_date():
    """Prompt for a ddmmyy start date until it parses."""
    while True:
        start_date_str = input("📅 Дата НАЧАЛА публикаций (ddmmyy): ").strip()
        try:
            return datetime.strptime(start_date_str, "%d%m%y")
        except ValueError:
            print("❌ Некорректная дата начала!")


def next_allowed_date(start_date, days_ahead, allowed_days):
    """Start date shifted forward, then nudged to the nearest allowed weekday."""
    current_date = start_date + timedelta(days=days_ahead)
    while current_date.strftime("%A") not in allowed_days:
        current_date += timedelta(days=1)
    return current_date


def get_channel_videos(youtube):
    """Uploads playlist entries for normal (non-live) videos, with their durations."""
    videos = []
    next_page_token = None
    response = youtube.channels().list(
        part="contentDetails",
        mine=True
    ).execute()
    uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    while True:
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        videos.extend(playlist_response['items'])
        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break

    filtered = []
    durations = {}
    video_ids = [item['snippet']['resourceId']['videoId'] for item in videos]
    found_ids = set()
    live_ids = set()
    # videos().list accepts up to 50 ids per call; batching saves a lot of quota.
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]
        details = youtube.videos().list(
            part="snippet,contentDetails", id=",".join(batch)
        ).execute()
        for video in details.get('items', []):
            found_ids.add(video['id'])
            durations[video['id']] = isodate.parse_duration(
                video['contentDetails']['duration']
            ).total_seconds()
            live_status = video['snippet'].get('liveBroadcastContent', 'none')
            if live_status in ['live', 'upcoming']:
                live_ids.add(video['id'])
    for item in videos:
        video_id = item['snippet']['resourceId']['videoId']
        if video_id in found_ids and video_id not in live_ids:
            filtered.append(item)
    return filtered, durations


def update_video_metadata(youtube, video_id, title, description, localizations):
    request = youtube.videos().list(part="snippet,localizations", id=video_id)
    response = request.execute()

    if not response['items']:
        print(f"Видео {video_id} не найдено")
        return False

    video = response['items'][0]

    body = {
        "id": video_id,
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": video['snippet'].get('tags', []),
            "categoryId": video['snippet']['categoryId'],
            "defaultLanguage": "en", 
            "enableAutoChapters": False
        }
    }

    merged_localizations = video.get('localizations', {}).copy()
    if localizations:
        for lang_code, texts in localizations.items():
            # ✅ ОБРЕЗАЕМ ВСЕ title до 100 символов!
            safe_title = texts['title'][:100]
            safe_desc = texts['description'][:5000]

            merged_localizations[lang_code] = {
                "title": safe_title,
                "description": safe_desc
            }
        body['localizations'] = merged_localizations

    youtube.videos().update(
        part="snippet,localizations",
        body=body
    ).execute()
    print(f"✅ {video_id} обновлено!")
    return True


def add_video_to_playlist(youtube, video_id, playlist_id):
    if not playlist_id:
        return
    # The videoId filter makes this a single quota-cheap lookup.
    existing = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        videoId=video_id,
        maxResults=1
    ).execute()
    if existing.get('items'):
        return  # Видео уже в плейлисте

    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    ).execute()



def normalize_description(text):
    """Decode copied HTML and keep paragraph breaks as normal newline characters."""
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Browser copies sometimes leave spaces on otherwise empty lines.
    text = re.sub(r"\n[ \t]+\n", "\n\n", text)
    return text.strip()


def get_description_from_dialog():
    """Open a multiline field so a browser description can be pasted as-is."""
    try:
        import tkinter
        from tkinter import messagebox, scrolledtext

        root = tkinter.Tk()
        root.title("Описание для перевода")
        root.geometry("760x700")
        root.minsize(760, 700)

        tkinter.Label(
            root,
            text="Вставь полное описание в поле ниже (Ctrl+V), затем нажми «Продолжить».",
            anchor="w",
            padx=12,
            pady=10,
        ).pack(fill="x")
        field = scrolledtext.ScrolledText(root, wrap="word", font=("Segoe UI", 11))
        field.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        result = {"text": None}

        def paste_from_clipboard(event=None):
            try:
                text = root.clipboard_get()
            except tkinter.TclError:
                messagebox.showerror(
                    "Буфер обмена",
                    "Не удалось получить текст из буфера. Сначала скопируй описание.",
                    parent=root,
                )
                return "break"
            field.insert("insert", text)
            field.focus_set()
            return "break"

        def confirm():
            result["text"] = field.get("1.0", "end-1c")
            root.destroy()

        def cancel():
            root.destroy()

        buttons = tkinter.Frame(root)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        tkinter.Button(buttons, text="Отмена", command=cancel).pack(side="right")
        tkinter.Button(buttons, text="Продолжить", command=confirm).pack(side="right", padx=(0, 8))
        tkinter.Button(buttons, text="Вставить из буфера", command=paste_from_clipboard).pack(side="left")
        root.protocol("WM_DELETE_WINDOW", cancel)
        field.bind("<Control-v>", paste_from_clipboard)
        field.bind("<Control-V>", paste_from_clipboard)
        field.focus_set()
        root.mainloop()

        if result["text"] is None:
            raise RuntimeError("Description entry was cancelled.")
        return result["text"]
    except Exception as error:
        raise RuntimeError(f"Could not enter the description: {error}") from error


def save_source_metadata(filename):
    """Ask for title and accept a complete, possibly multiline description."""
    title = input("\nEnter the English title: ").strip()
    if not title:
        raise ValueError("The title cannot be empty.")
    if len(title) > 100:
        raise ValueError("The title must be no longer than 100 characters.")

    print("\nОткроется поле для вставки полного описания.")
    description = normalize_description(get_description_from_dialog())
    if not description:
        raise ValueError("The description cannot be empty.")
    if len(description) > 5000:
        raise ValueError("The description must be no longer than 5000 characters.")

    metadata = {"title": title, "description": description}
    save_json_file(filename, metadata)
    return metadata



def load_local_llm_config():
    return load_json_file("local_llm.json")


_gemini_key_lock = threading.Lock()
_gemini_key_offset = 0
_gemini_dead_keys = set()  # keys that answered 404; skipped for the rest of the run


def parse_retry_hint(message):
    """Google puts an exact 'Please retry in 13.5s' hint into 429 messages."""
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


def load_gemini_api_keys():
    """Read Gemini API keys from data/gemini_api.json; several can be comma-separated."""
    if not os.path.exists(data_file_path(GEMINI_API_FILE)):
        raise FileNotFoundError(
            f'Нет файла data/{GEMINI_API_FILE}. Создай его с содержимым: '
            '{"GEMINI_API_KEY": "ключ1, ключ2, ..."}'
        )
    raw = load_json_file(GEMINI_API_FILE).get("GEMINI_API_KEY", "")
    keys = [key.strip() for key in re.split(r"[,\s]+", str(raw)) if key.strip()]
    if not keys:
        raise ValueError(f"{GEMINI_API_FILE} не содержит GEMINI_API_KEY.")
    return keys


def gemini_http_error(response):
    """HTTP status plus Google's own error text — the generic reason alone says nothing."""
    try:
        detail = response.json().get("error", {}).get("message", "")
    except ValueError:
        detail = ""
    return f"Gemini HTTP {response.status_code}: {detail or response.text[:300]}"


def request_gemini_completion(prompt, system_prompt, config):
    """One generateContent call against the Gemini API; returns raw JSON text.

    Keys are used round-robin. A key that answers 404 cannot see the model
    (API not enabled for its project, or not an AI Studio key), so the next
    key is tried within the same request instead of burning a retry.
    """
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
                "description": {"type": "STRING"}
            }
        },
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }
    if is_gemma:
        # Gemma rejects systemInstruction (HTTP 500) and thinkingBudget (400);
        # fold the system prompt into the user message instead.
        payload["contents"][0]["parts"][0]["text"] = f"{system_prompt}\n\n{prompt}"
    else:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        # Thinking eats output tokens without helping a fixed-format translation.
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}
    last_404 = None
    for offset in range(len(keys)):
        key = keys[(start + offset) % len(keys)]
        # Gemma answers transient 500s under load, Gemini 503s; both are
        # worth politely repeating within the same key before moving on.
        for patience in range(5):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers={"x-goog-api-key": key},
                    timeout=config.get("timeout_seconds", 180),
                )
            except requests.Timeout:
                if patience == 4:
                    raise
                print("⚠️ Таймаут запроса, жду 5с и пробую снова.")
                time.sleep(5)
                continue
            if response.status_code not in (500, 503) or patience == 4:
                break
            # Jitter keeps parallel language threads from retrying in sync.
            wait = 5 + random.uniform(0, 3)
            print(f"⚠️ {model} отвечает {response.status_code}, жду {wait:.0f}с и пробую снова.")
            time.sleep(wait)
        if response.status_code == 404:
            last_404 = gemini_http_error(response)
            if key not in _gemini_dead_keys:
                _gemini_dead_keys.add(key)
                live_left = len([k for k in all_keys if k not in _gemini_dead_keys])
                print(
                    f"⚠️ Ключ #{all_keys.index(key) + 1} не видит модель {model} — "
                    f"исключён до конца запуска. Рабочих ключей осталось: {live_left}."
                )
            continue
        if response.status_code != 200:
            raise RuntimeError(gemini_http_error(response))
        data = response.json()
        candidates = data.get("candidates") or [{}]
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        if not text:
            raise ValueError(f"Gemini вернул пустой ответ (finishReason={candidates[0].get('finishReason')})")
        return text
    raise RuntimeError(
        f"{last_404} — ни один из {len(all_keys)} ключей не видит модель {model}. "
        "Проверь название модели и что ключи из AI Studio с включённым Generative Language API."
    )


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


def load_codecraft_api_keys():
    """Read CodeCraft API keys from data/codecraft_api.json; comma-separated OK."""
    if not os.path.exists(data_file_path(CODECRAFT_API_FILE)):
        raise FileNotFoundError(
            f'Нет файла data/{CODECRAFT_API_FILE}. Создай его с содержимым: '
            '{"CODECRAFT_API_KEY": "cc_ключ1, cc_ключ2"} '
            "(ключ берётся в Dashboard → API Keys на codecraftapi.com)"
        )
    raw = load_json_file(CODECRAFT_API_FILE).get("CODECRAFT_API_KEY", "")
    keys = [key.strip() for key in re.split(r"[,\s]+", str(raw)) if key.strip()]
    if not keys:
        raise ValueError(f"{CODECRAFT_API_FILE} не содержит CODECRAFT_API_KEY.")
    return keys


_codecraft_key_lock = threading.Lock()
_codecraft_key_offset = 0


def load_ollama_api_keys():
    """Read Ollama API keys from data/ollama_api.json; several can be comma-separated."""
    if not os.path.exists(data_file_path(OLLAMA_API_FILE)):
        raise FileNotFoundError(
            f'Нет файла data/{OLLAMA_API_FILE}. Создай его с содержимым: '
            '{"OLLAMA_API_KEY": "ключ1, ключ2, ..."}'
        )
    raw = load_json_file(OLLAMA_API_FILE).get("OLLAMA_API_KEY", "")
    keys = [key.strip() for key in re.split(r"[,\s]+", str(raw)) if key.strip()]
    if not keys:
        raise ValueError(f"{OLLAMA_API_FILE} не содержит OLLAMA_API_KEY.")
    return keys


_ollama_key_lock = threading.Lock()
_ollama_key_offset = 0


def get_local_llm_model(config):
    """Return the configured model or the first model currently loaded in LM Studio."""
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


def parse_llm_json(content):
    """Accept plain JSON and recover JSON wrapped in a code block or with
    trailing chatter appended after the object (Gemma loves doing that)."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        content = content.rsplit("```", 1)[0].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # "Extra data: ..." means valid JSON followed by extra text;
        # keep only the first JSON value.
        value, _ = json.JSONDecoder().raw_decode(content)
        return value


def load_series_names():
    """Known channel/series names; grows as channels are authorized on this machine."""
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
    """Drop LLM-invented series footer lines.

    A line naming a known channel/series is only kept when the source
    description mentions that name itself; otherwise it's a model invention.
    """
    series_names = load_series_names()
    if not series_names:
        return description
    source_casefold = source_description.casefold()
    kept = []
    for line in description.split("\n"):
        invented = any(
            name.casefold() in line.casefold()
            and name.casefold() not in source_casefold
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
        # The model merged or split lines; its own breaks are the best we have.
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
    """Clean old localized descriptions produced before the footer guard existed."""
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


def request_lmstudio_completion(endpoint, model, prompt, system_prompt, config):
    """One OpenAI-compatible chat completion against LM Studio; returns raw text."""
    schema = {
        "name": "localized_metadata",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "description"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.get("temperature", 0.25),
        "max_tokens": config.get("max_tokens", 2400),
        "stream": False,
        "response_format": {"type": "json_schema", "json_schema": schema},
    }
    response = requests.post(
        f"{endpoint}/chat/completions",
        json=payload,
        timeout=config.get("timeout_seconds", 180),
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def request_ollama_completion(prompt, system_prompt, config):
    """One chat completion against Ollama's cloud API (OpenAI-compatible); raw text.

    Keys rotate round-robin; a dead key (401/403/404) is skipped within the
    same request instead of burning a retry.
    """
    global _ollama_key_offset
    keys = load_ollama_api_keys()
    with _ollama_key_lock:
        start = _ollama_key_offset % len(keys)
        _ollama_key_offset += 1
    endpoint = config.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model = config.get("ollama_model", DEFAULT_OLLAMA_MODEL)
    schema = {
        "name": "localized_metadata",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "description"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.get("temperature", 0.25),
        "max_tokens": config.get("max_tokens", 2400),
        "stream": False,
        "response_format": {"type": "json_schema", "json_schema": schema},
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
            print(f"⚠️ Ollama-ключ #{start + offset + 1} не работает, пробую следующий.")
            continue
        if response.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {response.status_code}: {response.text[:300]}")
        answer = response.json()
        content = answer.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise ValueError(f"Ollama вернул пустой ответ: {str(answer)[:200]}")
        return content
    raise RuntimeError(f"{last_error} — ни один из {len(keys)} Ollama-ключей не сработал.")


def request_codecraft_completion(prompt, system_prompt, config):
    """One chat completion against codecraftapi.com (OpenAI-compatible); raw text.

    Key rotation helps only when keys belong to different accounts: the
    per-plan rate limits are shared by all keys of one account. A 429 carries
    a Retry-After header, which is echoed into the error for the retry parser.
    """
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
        # Reasoning models spend tokens on thinking before the answer, and
        # thinking counts toward max_tokens — a tight cap leaves content empty.
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
            print(f"⚠️ CodeCraft-ключ #{start + offset + 1} не работает, пробую следующий.")
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
                f"CodeCraft вернул пустой ответ (finish_reason={choice.get('finish_reason')}): "
                f"{str(answer)[:150]}"
            )
        return content
    raise RuntimeError(f"{last_error} — ни один из {len(keys)} CodeCraft-ключей не сработал.")


def localize_language_via_llm(provider, endpoint, model, config, language_code,
                               language_name, source_title, source_description):
    """Localize metadata for one language; raises after the final retry fails."""
    # One working free-tier key allows ~5 requests/minute, so Gemini needs
    # more attempts to wait out 429s across all queued languages.
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
            # Google names the exact wait in 429 messages; 500/503 are server flakiness.
            wait_seconds = parse_retry_hint(message)
            if wait_seconds is None:
                if "429" in message:
                    wait_seconds = 20
                elif "500" in message or "503" in message:
                    wait_seconds = 10
                else:
                    wait_seconds = 2
            print(f"RETRY {language_code} ({attempt}/{max_attempts - 1}), жду {wait_seconds}с: "
                  f"{message.splitlines()[0]}")
            time.sleep(wait_seconds)


def localize_metadata_via_llm(metadata, localizations, target_languages=None):
    """Create localized titles and descriptions through Gemini, Ollama, CodeCraft or LM Studio."""
    config = load_local_llm_config()
    provider = resolve_llm_provider(config)
    endpoint = config["base_url"].rstrip("/")
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
        raise ValueError("metadata.json must contain a non-empty title and description.")

    if target_languages is None:
        target_languages = list(localizations.keys())
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
        max_workers = min(len(queued), max(1, config.get("max_parallel_languages", 5)))
        print(f"🧵 Переводим {len(queued)} языков, одновременно до {max_workers}.")
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            def delayed(idx, code):
                # Stagger starts so all threads don't slam the model at once.
                time.sleep(idx * 1.5)
                return localize_language_via_llm(
                    provider, endpoint, model, config,
                    code, language_names.get(code, code), source_title, source_description,
                )
            futures = {
                pool.submit(delayed, idx, code): code
                for idx, code in enumerate(queued)
            }
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
        raise RuntimeError("Localization was not saved because some languages failed:\n" + "\n".join(errors))

    ordered = {code: translated[code] for code in target_languages if code in translated}
    save_json_file(LOCALIZATIONS_FILE, ordered)
    print(f"Localized title and description for {len(ordered)} languages using {model}.")


def fetch_video_source_metadata(youtube, video_id):
    """Read the video's current title and description from YouTube as the source."""
    response = youtube.videos().list(part="snippet", id=video_id).execute()
    if not response.get('items'):
        raise ValueError(f"Видео {video_id} не найдено.")
    snippet = response['items'][0]['snippet']
    metadata = {
        "title": (snippet.get("title") or "").strip(),
        "description": normalize_description(snippet.get("description") or ""),
    }
    if not metadata["title"] or not metadata["description"]:
        raise ValueError(f"У видео {video_id} пустое название или описание.")
    if len(metadata["title"]) > 100 or len(metadata["description"]) > 5000:
        raise ValueError(
            f"Данные видео превышают лимиты: title={len(metadata['title'])}, "
            f"description={len(metadata['description'])}"
        )
    return metadata


def run_localization(metadata, profile):
    """Translate metadata into the profile's languages and save localizations.json."""
    localizations = load_json_file(LOCALIZATIONS_FILE)
    if clean_existing_series_footers(localizations, metadata["description"]):
        save_json_file(LOCALIZATIONS_FILE, localizations)
    target_languages = get_profile_languages(profile)
    if not target_languages:
        print("\nНе выбран ни один язык перевода. Открой пункт 6 и отметь нужные языки.")
        return False
    print(
        "Название и описание приняты в работу. "
        f"Ведётся перевод на {len(target_languages)} языковых версий...\n"
    )
    try:
        localize_metadata_via_llm(metadata, localizations, target_languages)
    except Exception as error:
        print(f"\nLocalization was not saved: {error}")
        return False
    return True


def what_else():
    answer = input("\nЧто-то еще? (Да/Нет): ").strip().lower()
    clear_console()
    return answer in ['д', 'да', 'y', 'yes']


def main():
    profile, profiles = select_channel_profile()
    youtube = authenticate(profile)
    refresh_profile_identity(youtube, profile, profiles)
    print(f"\nActive channel: {profile['channel_title']}")
    publ_calendar = load_json_file(profile["publ_calendar_file"])
    playlist_id = profile.get("playlist_id", "")
    clear_console()

    ALLOWED_DAYS = ['Monday', 'Wednesday', 'Friday', 'Sunday']

    while True:
        print("""\nПривет, Мастер, что обновляем?

1) Последнее видео
2) Конкретные видео
3) Все видео
4) Локализуй название и описание (Gemini / LM Studio)
5) Отложенная публикация по ссылке
6) Настройки языков перевода""")
        choice = input("\nВыбери 1, 2, 3, 4, 5 или 6: ").strip()
        clear_console()

        if choice == '1':
            videos = []
            try:
                videos, _ = get_channel_videos(youtube)
            except HttpError as e:
                if "quotaExceeded" in str(e):
                    print("\nЛимит квоты на сегодня превышен. Подожди до завтра.")
                    if not what_else():
                        return
                else:
                    raise

            if not videos:
                print("Нет доступных видео для обновления.")
                if not what_else():
                    return
                continue

            videos.sort(key=lambda x: x['snippet']['publishedAt'], reverse=True)
            last_video = videos[0]
            video_id = last_video['snippet']['resourceId']['videoId']
            print(f"Последнее видео: {video_id} — {last_video['snippet']['title']}")

            while True:
                print("""
Откуда взять название и описание?

1) Перевести актуальные данные с видео (берутся с YouTube и применяются сюда же)
2) Загрузить локальный перевод (metadata.json + localizations.json)
0) Назад""")
                source_choice = input("\nВыбери 1, 2 или 0: ").strip()
                clear_console()

                if source_choice == "0":
                    break

                if source_choice == "1":
                    try:
                        metadata = fetch_video_source_metadata(youtube, video_id)
                    except (ValueError, HttpError) as error:
                        print(f"\n❌ Не удалось взять данные с видео: {error}")
                        continue
                    print(f"Название: {metadata['title']}")
                    print(f"Описание: {len(metadata['description'])} символов")
                    save_json_file(METADATA_FILE, metadata)
                    if not run_localization(metadata, profile):
                        continue
                    localizations = load_json_file(LOCALIZATIONS_FILE)
                else:
                    metadata = load_json_file(METADATA_FILE)
                    localizations = load_json_file(LOCALIZATIONS_FILE)

                updated = update_video_metadata(
                    youtube, video_id, metadata.get('title'), metadata.get('description'), localizations
                )

                if updated:
                    add_video_to_playlist(youtube, video_id, playlist_id)

                    do_schedule = input(f"\n📅 Отложенная публикация для {video_id}? (да/нет): ").strip().lower() in ['д', 'да', 'y', 'yes']
                    if do_schedule:
                        publish_datetime = ask_publish_date(publ_calendar, ALLOWED_DAYS)
                        set_publishAt(youtube, video_id, publish_datetime)

                    print(f'\n✅ Видео "{video_id}" обновлено и добавлено в плейлист{" + отложка" if do_schedule else ""}.')
                if not what_else():
                    return
                break

        elif choice == '2':
            video_urls_input = input("\nВведи одну или несколько ссылок на видео (через запятую или пробел): ").strip()
            clear_console()
            video_urls = [url.strip() for url in re.split(r'[,\s]+', video_urls_input) if url.strip()]

            try:
                metadata = load_json_file(METADATA_FILE)
                localizations = load_json_file(LOCALIZATIONS_FILE)
            except FileNotFoundError:
                print("\nНет сохранённого перевода. Сначала сделай перевод (пункт 1 или 4).")
                if not what_else():
                    return
                continue

            # ✅ Счетчик для автоматического планирования по дням
            schedule_index = 0
            start_date = None

            for video_url in video_urls:
                try:
                    video_id = extract_video_id(video_url)
                    if not video_id:
                        print(f"\n❌ Не удалось извлечь ID из: {video_url}")
                        continue

                    updated = update_video_metadata(
                        youtube, video_id, metadata.get('title'), metadata.get('description'), localizations
                    )

                    if updated:
                        do_add_playlist = input(f"\n➕ Добавить {video_id} в плейлист? (да/нет): ").strip().lower() in ['д', 'да', 'y', 'yes']
                        clear_console()
                        if do_add_playlist:
                            add_video_to_playlist(youtube, video_id, playlist_id)

                        # ✅ АВТОМАТИЧЕСКОЕ планирование по дням недели
                        do_schedule = input(f"📅 Отложенная публикация для {video_id}? (да/нет): ").strip().lower() in ['д', 'да', 'y', 'yes']
                        if do_schedule:
                            if start_date is None:
                                start_date = ask_start_date()

                            publish_date = next_allowed_date(start_date, schedule_index * 2, ALLOWED_DAYS)
                            publish_datetime, publish_time = to_publish_datetime(publish_date, publ_calendar)

                            print(f"📱 {video_id} → {publish_date.strftime('%A')} {publish_date.strftime('%d.%m.%y')} {publish_time}")
                            set_publishAt(youtube, video_id, publish_datetime)
                            schedule_index += 1

                        print(f'\n✅ "{video_id}" обновлено{" + плейлист" if do_add_playlist else ""}{" + отложка" if do_schedule else ""}.')
                    else:
                        print(f"\n❌ Не удалось обновить {video_id}.")
                except HttpError as e:
                    if "quotaExceeded" in str(e):
                        print("\nЛимит квоты превышен.")
                        if not what_else():
                            return
                    else:
                        raise

            if not what_else():
                return


        elif choice == '3':
            qty_choice = ''
            max_updates_per_run = 0

            while True:
                print("""\nСколько видео обновить?

1) Все видео на канале
2) Ввести своё количество""")
                qty_choice = input("\nВыбери 1 или 2: ").strip()
                clear_console()
                if qty_choice in ['1', '2']:
                    break
                else:
                    print("Некорректный выбор.")

            if qty_choice == '1':
                max_updates_per_run = float('inf')
            else:
                while True:
                    qty_input = input("\nКоличество последних видео для обновления: ").strip()
                    clear_console()
                    if qty_input.isdigit() and int(qty_input) > 0:
                        max_updates_per_run = int(qty_input)
                        break
                    else:
                        print("\nПожалуйста, введи положительное число.")

            do_schedule_all = input("\n📅 Делать отложенную публикацию для всех? (да/нет): ").strip().lower() in ['д', 'да', 'y', 'yes']

            try:
                videos, durations = get_channel_videos(youtube)
            except HttpError as e:
                if "quotaExceeded" in str(e):
                    print("\nЛимит квоты превышен.")
                    if not what_else():
                        return
                else:
                    raise

            videos.sort(key=lambda x: x['snippet']['publishedAt'], reverse=True)
            try:
                metadata = load_json_file(METADATA_FILE)
                localizations = load_json_file(LOCALIZATIONS_FILE)
            except FileNotFoundError:
                print("\nНет сохранённого перевода. Сначала сделай перевод (пункт 1 или 4).")
                if not what_else():
                    return
                continue

            updated_count = 0
            schedule_index = 0
            start_date = None

            for item in videos:
                if updated_count >= max_updates_per_run:
                    print(f"\nДостигнут лимит обновлений ({max_updates_per_run}).")
                    break

                video_id = item['snippet']['resourceId']['videoId']

                # Durations and live status were already fetched in the batched
                # get_channel_videos call, so no per-video quota is spent here.
                if durations.get(video_id, 0) <= 60:
                    continue

                updated = update_video_metadata(
                    youtube, video_id, metadata.get('title'), metadata.get('description'), localizations
                )

                if updated:
                    updated_count += 1
                    limit_display = "∞" if max_updates_per_run == float('inf') else max_updates_per_run
                    print(f'✅ Обновлено видео "{video_id}" ({updated_count}/{limit_display}).')
                    
                    # ✅ АВТОМАТИЧЕСКОЕ планирование для пункта 3
                    if do_schedule_all:
                        if start_date is None:
                            start_date = ask_start_date()

                        publish_date = next_allowed_date(start_date, schedule_index * 2, ALLOWED_DAYS)
                        publish_datetime, publish_time = to_publish_datetime(publish_date, publ_calendar)

                        print(f"📱 {video_id} → {publish_date.strftime('%A')} {publish_date.strftime('%d.%m.%y')} {publish_time}")
                        set_publishAt(youtube, video_id, publish_datetime)
                        schedule_index += 1

            print(f"\n✅ Всего обновлено {updated_count} видео.")
            if not what_else():
                return
        
        elif choice == '4':
            clear_console()
            try:
                metadata = save_source_metadata(METADATA_FILE)
            except (ValueError, RuntimeError) as error:
                print(f"\nMetadata was not saved: {error}")
                continue
            clear_console()
            run_localization(metadata, profile)
            continue

        elif choice == '5':
            while True:
                url = input("\n📹 Вставь ссылку на видео: ").strip()
                video_id = extract_video_id(url)
                if video_id:
                    break
                print("❌ Некорректная ссылка!")

            print(f"📱 Видео ID: {video_id}")
            publish_datetime = ask_publish_date(publ_calendar, ALLOWED_DAYS)

            if set_publishAt(youtube, video_id, publish_datetime):
                print(f"✅ Готово! {video_id} опубликуется {publish_datetime.strftime('%d.%m.%Y %H:%M UTC')}")
            if not what_else():
                return

        elif choice == '6':
            clear_console()
            manage_profile_languages(profile, profiles)
            continue

        else:
            print("❌ Некорректный выбор. Выбери 1, 2, 3, 4, 5 или 6.")
            continue



if __name__ == "__main__":
    main()
