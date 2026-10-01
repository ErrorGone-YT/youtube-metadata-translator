# YouTube Metadata Translator

A CLI tool for YouTube creators: it localizes video titles and descriptions into 12+ languages with an AI model (CodeCraft/DeepSeek, Google Gemini, Ollama or a local LM Studio), updates video metadata, adds videos to playlists and schedules publishing for specific weekdays.

Works on Windows and macOS. Everything it needs is free or nearly free.

> 🇺🇦 Інструкція українською: [README.uk.md](README.uk.md)
> 🇷🇺 Инструкция на русском: [README.ru.md](README.ru.md)

## What you need (~30 minutes of one-time setup)

1. **Python 3.10 or newer** — the language the script is written in.
2. A **Google account** that owns the YouTube channel.
3. A **translation API key** — one of:
   - [CodeCraft API](https://codecraftapi.com) — the most stable option, has a free tier;
   - Google **Gemini** keys — free, but the model is sometimes overloaded.
4. ~30 minutes for the setup (done once).

## Step 1. Install Python

### Windows

1. Go to https://www.python.org/downloads/ and press the yellow **Download Python 3.x.x** button.
2. Run the installer.
3. **MOST IMPORTANT:** on the first screen check **"Add python.exe to PATH"** (at the bottom).
4. Press **Install Now**.
5. Check: press `Win + R`, type `cmd`, press Enter, then type `python --version`. It should print something like `Python 3.13.1`.

### macOS

1. Go to https://www.python.org/downloads/ — the site offers the right version for Mac. Install it like a normal app.
2. Check: open **Terminal** (Cmd + Space, type "Terminal"), type `python3 --version`.
3. `tkinter` (needed for the description input window) comes with the python.org installer automatically.

## Step 2. Install the libraries

Open a terminal in the project folder and run:

```
pip install -r requirements.txt
```

(macOS: `pip3 install -r requirements.txt`)

## Step 3. Create your Google keys (client_secrets) — the longest step

These keys let the script manage **your** YouTube channel. Done once.

### 3.1. Create a Google Cloud project

1. Go to https://console.cloud.google.com with the Google account of your channel.
2. Top bar → project selector → **New Project**.
3. Name it anything, e.g. `youtube-translator` → **Create**.

### 3.2. Enable the YouTube Data API

1. Menu (☰) → **APIs & Services** → **Library**.
2. Search for `YouTube Data API v3` → open it → press **Enable**.

### 3.3. Configure the OAuth consent screen

1. Menu → **APIs & Services** → **OAuth consent screen** (may be called **Google Auth Platform**).
2. **User Type**: **External** → **Create**.
3. Fill in the minimum: **App name** (anything), **User support email** (your email), **Developer contact email**.
4. Press **Save and Continue** on every step (Scopes can be skipped).

### 3.4. Add emails to Test users — REQUIRED

While the app is in **Testing** mode, Google only lets in **users whose emails you explicitly added**. Otherwise you'll get `Access blocked: access_denied`.

1. In **OAuth consent screen** (or **Google Auth Platform → Audience**) find **Test users**.
2. Press **+ Add Users**.
3. Enter **the email of your channel's Google account** (and the email of anyone else who will use the script).
4. **Save**.

> ⚠️ In Testing mode the access token lives **7 days**, then the script asks you to sign in again. Tired of that? Press **Publish App** on the consent screen — sign-in then works indefinitely (Google may show an "unverified app" warning; for personal use just press Advanced → Go to the app).

### 3.5. Download client_secrets

1. Menu → **APIs & Services** → **Credentials**.
2. **+ Create Credentials** → **OAuth client ID**.
3. **Application type**: **Desktop app** (not Web, not Android!).
4. Name it anything → **Create** → **Download JSON**.
5. Rename the file to **`client_secrets.json`**.
6. Put it into the **`data`** folder next to the script.

> 💡 Managing **several channels**? Each channel needs its own `client_secrets.json` (from that channel's Google account) and its own profile. Files can have different names — the script asks for the filename when creating a profile and auto-detects any `client_secrets*.json` in `data/`.

## Step 4. Connect a translation provider

The script detects the provider automatically from the key file you create in `data/`.

### Option A — CodeCraft API (recommended: stable, fast, cheap)

1. Sign up at https://codecraftapi.com (free tier: 1M tokens/month ≈ 60 full translations).
2. **Dashboard → API Keys → Create Key**. Keys start with `cc_` and are shown **once** — copy immediately.
3. Create **`data/codecraft_api.json`** (the key must be in quotes!):

```json
{ "CODECRAFT_API_KEY": "cc_your_key_here" }
```

4. Default model: `deepseek-v4-flash-0731` (great quality at $0.12 per million tokens ≈ half a cent per video). Other models: https://codecraftapi.com/models, switch via `codecraft_model` in `data/local_llm.json`.

### Option B — Gemini keys from Google (free)

1. Go to https://aistudio.google.com/apikey.
2. **Create API key** → copy (starts with `AIza...`).
3. Create **several keys** — they work as a pool with automatic rotation.
4. Create **`data/gemini_api.json`**:

```json
{ "GEMINI_API_KEY": "AIza_key1, AIza_key2, AIza_key3" }
```

> Gemini sometimes answers "model overloaded" — the script retries patiently, runs just take a bit longer. CodeCraft is more stable.

## Step 5. First run

### Windows

Double-click **Запустить (Windows).cmd**.

### macOS

1. Open Terminal, type `chmod +x ` (with a trailing space), drag **Запустить (Mac).command** into the window, press Enter. One-time only.
2. After that just double-click the file.
3. If macOS says the file is from the internet: System Settings → Privacy & Security → "Open Anyway".

### First-launch wizard

1. **Language** — English / Українська / Русский.
2. **Your name** — how the script addresses you.
3. **Profile name** — anything.
4. The script finds your `client_secrets*.json` automatically.
5. **Playlist ID** — optional (Enter to skip).
6. A browser window opens — **sign in to the channel's Google account**. If Google warns about an unverified app: Advanced → Go to the app.
7. Done — the token is saved in `data/tokens/`, no repeated sign-ins.

Until the setup is finished, the menu shows **Settings only**. Setup is complete once you've chosen translation languages (Settings) and added a translation key.

## Menu

| Item | What it does |
|---|---|
| **Translation** | Takes the actual title/description of a video, localizes them into the selected languages and applies them back. |
| **Add to playlist** | Adds videos to the profile's playlist. |
| **Scheduled publishing** | Schedules a video for a specific date. |
| **Settings** | Interface language, your name, translation languages, parallel translations. |

## Files and folders

```
youtube-metadata-translator/
├── yt_metadata_translator.py ← the script
├── Запустить (Windows).cmd   ← Windows launcher
├── Запустить (Mac).command   ← macOS launcher
├── requirements.txt          ← library list
├── README.md                 ← this guide
└── data/                     ← all data (put your key files here)
    ├── local_llm.json        ← translator settings
    ├── client_secrets.json   ← Google keys (step 3.5)
    ├── codecraft_api.json    ← CodeCraft key (step 4, option A)
    ├── gemini_api.json       ← Gemini keys (step 4, option B)
    ├── channel_profiles.json ← channel profiles (auto-created)
    ├── metadata.json         ← last translated title/description
    ├── localizations.json    ← last set of translations
    ├── ui_settings.json      ← interface language and your name (auto-created)
    └── tokens/               ← saved Google sign-ins (auto-created)
```

Enjoy! 🧙
