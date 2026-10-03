"""YouTube Metadata Translator — web interface.

Local stdlib-only server (no new dependencies): serves the SPA from
webui_static/ and exposes a JSON API over yt_metadata_translator.
Run:  python webui.py   (opens the browser automatically)
"""
import json
import os
import re
import shutil
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yt_metadata_translator as eng

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "webui_static")
PORT_RANGE = range(8765, 8790)

# ---------------------------------------------------------------------------
# Shared job state (translation runs in a background thread; the UI polls)
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()
CLIENTS = {}          # profile_id -> authorized youtube client
THREAD_JOB = {}       # thread ident -> job id, used by the stdout tee
JOBS = {}             # job id -> state dict
JOB_SEQ = 0
AUTH = {"running": False, "ok": None, "error": "", "channel": "", "profile_id": ""}


def new_job(kind):
    global JOB_SEQ
    with _LOCK:
        JOB_SEQ += 1
        job = {"id": JOB_SEQ, "kind": kind, "running": True, "done": False,
               "error": "", "log": [], "videos_total": 0, "videos_done": 0,
               "video_title": "", "langs": {}, "started": time.time()}
        JOBS[JOB_SEQ] = job
        return job


def job_progress(job, state, code, detail=""):
    with _LOCK:
        job["langs"][code] = {"state": state, "detail": detail}


def job_log(job, text):
    with _LOCK:
        job["log"].append(str(text))
        del job["log"][:-400]  # keep the tail only


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class _JobTee:
    """sys.stdout replacement: engine prints from a job thread go to that job's log."""

    def __init__(self, origin):
        self.origin = origin

    def write(self, text):
        job_id = THREAD_JOB.get(threading.get_ident())
        line = _ANSI.sub("", str(text)).strip()
        if job_id and line:
            job = JOBS.get(job_id)
            if job:
                with _LOCK:
                    job["log"].append(line)
                    del job["log"][:-400]
        return self.origin.write(text)

    def flush(self):
        self.origin.flush()


# ---------------------------------------------------------------------------
# Helpers over the engine
# ---------------------------------------------------------------------------

def get_client(profile):
    """Authorized youtube client for the profile; refreshes the token silently."""
    client = CLIENTS.get(profile["profile_id"])
    if client:
        return client
    client = eng.authenticate(profile)  # works without a browser when the token is valid
    CLIENTS[profile["profile_id"]] = client
    return client


def profile_brief(profile):
    return {
        "id": profile["profile_id"],
        "name": profile.get("channel_title") or profile.get("display_name"),
        "ready": eng.profile_is_ready(profile),
        "authorized": bool(profile.get("channel_id")),
        "languages": eng.get_profile_languages(profile),
        "playlists": profile.get("playlists", []),
        "default_playlists": profile.get("default_playlists", []),
    }


def find_profile(profile_id):
    for profile in eng.load_channel_profiles()["profiles"]:
        if profile["profile_id"] == profile_id:
            return profile
    raise ValueError("profile not found")


def update_profile(profile_id, mutate):
    """Mutate one profile inside the loaded list and save — saving a fresh
    eng.load_channel_profiles() would silently drop the change (the engine
    re-reads the file on every call)."""
    profiles = eng.load_channel_profiles()
    for profile in profiles["profiles"]:
        if profile["profile_id"] == profile_id:
            mutate(profile)
            eng.save_channel_profiles(profiles)
            return profile
    raise ValueError("profile not found")


def active_profile():
    saved = eng._ui.get("web_active_profile")
    profiles = eng.load_channel_profiles()["profiles"]
    for profile in profiles:
        if profile["profile_id"] == saved:
            return profile
    return profiles[0] if profiles else None


def create_profile(name, secrets_filename, secrets_content):
    """New profile + client_secrets file uploaded from the browser."""
    json.loads(secrets_content)  # raises when the picked file is not JSON
    profiles = eng.load_channel_profiles()
    profile_id = eng.profile_slug(name, {p["profile_id"] for p in profiles["profiles"]})
    secrets_name = secrets_filename if str(secrets_filename).startswith("client_secrets") \
        else f"client_secrets_{profile_id}.json"
    dest = eng.data_file_path(secrets_name)
    if not os.path.exists(dest):
        with open(dest, "w", encoding="utf-8") as f:
            f.write(secrets_content)
    profile = {
        "profile_id": profile_id,
        "display_name": name,
        "channel_id": "",
        "channel_title": "",
        "token_file": f"profiles/{profile_id}/token.pickle",
        "client_secrets_file": secrets_name,
        "playlists": [],
        "default_playlists": [],
        "languages": [],
        "publ_calendar_file": f"profiles/{profile_id}/calendar.json",
    }
    profiles["profiles"].append(profile)
    eng.save_channel_profiles(profiles)
    eng.save_json_file(profile["publ_calendar_file"], {})
    return profile


def start_auth(profile):
    def worker():
        try:
            client = eng.authenticate(profile)
            eng.refresh_profile_identity(client, profile, eng.load_channel_profiles())
            CLIENTS[profile["profile_id"]] = client
            AUTH.update(running=False, ok=True, error="",
                        channel=profile.get("channel_title") or profile.get("display_name"))
        except Exception as error:
            AUTH.update(running=False, ok=False, error=str(error))
    threading.Thread(target=worker, daemon=True).start()


def start_translation(payload):
    profile = active_profile()
    if profile is None:
        raise ValueError("no profile")
    client = get_client(profile)
    job = new_job("translate")

    mode = payload.get("mode", "last")
    want_short = bool(payload.get("want_short"))
    links = [line.strip() for line in payload.get("links", []) if line.strip()]
    manual = payload.get("source") == "manual"
    manual_title = str(payload.get("manual_title", "")).strip()
    manual_desc = str(payload.get("manual_desc", "")).strip()
    parts = payload.get("parts", ("title", "description"))
    langs = [c for c in payload.get("langs", []) if c and c != "en"]
    add_playlists = bool(payload.get("add_playlists"))
    do_schedule = bool(payload.get("do_schedule"))
    schedule_date = str(payload.get("schedule_date", "")).strip()

    def progress(state, code, detail=""):
        job_progress(job, state, code, detail)

    def worker():
        THREAD_JOB[threading.get_ident()] = job["id"]
        try:
            job_log(job, f"🎬 {eng.t('translating').format(n=len(langs))}")
            videos, durations = eng.get_channel_videos(client)
            videos.sort(key=lambda x: x["snippet"]["publishedAt"], reverse=True)
            if mode == "specific":
                targets = [v for v in (eng.extract_video_id(link) for link in links) if v]
            else:
                targets = eng._pick_translation_targets(
                    videos, durations, ("last_short" if want_short else "last_long")
                    if mode == "last" else ("all_short" if want_short else "all_long"))
            if not targets:
                job_log(job, eng.t("tr_no_matches"))
                return
            with _LOCK:
                job["videos_total"] = len(targets)
            for video_id in targets:
                try:
                    metadata = eng.fetch_video_source_metadata(client, video_id)
                except Exception as error:
                    job_log(job, f"❌ {error}")
                    continue
                if manual:
                    if manual_title:
                        metadata["title"] = manual_title
                    if manual_desc:
                        metadata["description"] = eng.normalize_description(manual_desc)
                eng.save_json_file(eng.METADATA_FILE, metadata)
                with _LOCK:
                    job["video_title"] = metadata["title"]
                job_log(job, f"🎬 {video_id} — {metadata['title']}")
                try:
                    eng.localize_metadata_via_llm(metadata, langs, parts, progress=progress)
                except Exception as error:
                    job_log(job, f"❌ {error}")
                    continue
                localizations = eng.load_json_file(eng.LOCALIZATIONS_FILE)
                try:
                    eng.update_video_metadata(
                        client, video_id,
                        metadata.get("title"), metadata.get("description"), localizations)
                    job_log(job, eng.t("video_updated").format(id=video_id))
                except Exception as error:
                    job_log(job, f"❌ {error}")
                    continue
                if add_playlists:
                    for pl_id in profile.get("default_playlists", []):
                        try:
                            eng.add_video_to_playlist(client, video_id, pl_id)
                            job_log(job, f"➕ {pl_id}")
                        except Exception as error:
                            job_log(job, f"❌ {error}")
                if do_schedule:
                    try:
                        publish_date = eng.datetime.strptime(schedule_date, "%d%m%y")
                        publish_datetime, _ = eng.to_publish_datetime(
                            publish_date, eng.load_calendar(profile))
                        eng.set_publishAt(client, video_id, publish_datetime)
                    except ValueError:
                        job_log(job, "⚠️ ddmmyy")
                with _LOCK:
                    job["videos_done"] += 1
            job_log(job, "✅ " + (eng.t("tr_done_all") if eng.STRINGS.get(eng._ui.get("language"), {}).get("tr_done_all") else "Done"))
        except Exception as error:
            with _LOCK:
                job["error"] = str(error)
            job_log(job, f"❌ {error}")
        finally:
            THREAD_JOB.pop(threading.get_ident(), None)
            with _LOCK:
                job["running"] = False
                job["done"] = True

    threading.Thread(target=worker, daemon=True).start()
    return job


def schedule_video(payload):
    profile = active_profile()
    client = get_client(profile)
    video_id = eng.extract_video_id(str(payload.get("link", "")))
    if not video_id:
        raise ValueError("bad link")
    publish_date = eng.datetime.strptime(str(payload.get("date", "")).strip(), "%d%m%y")
    publish_datetime, publish_time = eng.to_publish_datetime(
        publish_date, eng.load_calendar(profile))
    if not eng.set_publishAt(client, video_id, publish_datetime):
        raise ValueError("YouTube refused the schedule")
    return {"video_id": video_id,
            "when": publish_datetime.strftime("%d.%m.%Y %H:%M"), "time": publish_time}


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
        ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}


class Handler(BaseHTTPRequestHandler):
    server_version = "YTMetadataWeb/1.0"

    # --- plumbing ---

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # keep the console quiet

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/":
                return self._file("index.html")
            if path.startswith("/static/"):
                return self._file(path[len("/static/"):])
            if path == "/api/bootstrap":
                return self.api_bootstrap()
            if path == "/api/job":
                return self.api_job()
            if path == "/api/auth":
                return self._json(dict(AUTH))
            if path == "/api/providers":
                return self._json(eng.load_provider_registry())
            return self._json({"error": "not found"}, 404)
        except Exception as error:
            self._json({"error": str(error)}, 500)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            data = self._body()
            if path == "/api/quit":
                threading.Timer(0.3, os._exit, (0,)).start()
                return self._json({"ok": True})
            if path == "/api/onboarding":
                eng._ui["language"] = data.get("language")
                eng._ui["user_name"] = str(data.get("name", "")).strip()
                eng.save_ui_settings()
                return self._json({"ok": True})
            if path == "/api/ui":
                for key in ("language", "user_name", "ask_playlists", "ask_schedule",
                            "language_presets", "web_active_profile"):
                    if key in data:
                        eng._ui[key] = data[key]
                eng.save_ui_settings()
                return self._json({"ok": True})
            if path == "/api/profiles":
                profile = create_profile(str(data.get("name", "")).strip(),
                                         str(data.get("secrets_filename", "")),
                                         str(data.get("secrets_content", "")))
                return self._json(profile_brief(profile))
            if path == "/api/auth":
                profile = find_profile(data["profile_id"])
                if AUTH["running"]:
                    return self._json({"error": "already running"}, 409)
                AUTH.update(running=True, ok=None, error="", channel="",
                            profile_id=profile["profile_id"])
                start_auth(profile)
                return self._json({"ok": True})
            if path == "/api/profile/languages":
                codes = [str(c) for c in data.get("codes", []) if eng.valid_language_code(c)]
                profile = update_profile(
                    data["profile_id"], lambda p: p.__setitem__("languages", sorted(set(codes))))
                return self._json({"ok": True})
            if path == "/api/translate":
                return self._json({"ok": True, "job": start_translation(data)["id"]})
            if path == "/api/schedule":
                return self._json(schedule_video(data))
            if path == "/api/playlists/add":
                playlist_id = eng.parse_playlist_id(str(data.get("link", "")))
                if not playlist_id:
                    raise ValueError("bad playlist link")

                def _add(p):
                    client = get_client(p)
                    if not any(pl["id"] == playlist_id for pl in p.setdefault("playlists", [])):
                        title = eng.fetch_playlist_title(client, playlist_id)
                        p["playlists"].append(
                            {"id": playlist_id,
                             "name": str(data.get("name", "")).strip() or title or playlist_id})

                profile = update_profile(data["profile_id"], _add)
                return self._json(profile_brief(profile))
            if path == "/api/playlists/remove":
                def _remove(p):
                    p["playlists"] = [pl for pl in p.get("playlists", [])
                                      if pl["id"] != data["playlist_id"]]
                    ds = p.setdefault("default_playlists", [])
                    if data["playlist_id"] in ds:
                        ds.remove(data["playlist_id"])
                profile = update_profile(data["profile_id"], _remove)
                return self._json(profile_brief(profile))
            if path == "/api/playlists/default":
                def _default(p):
                    ds = p.setdefault("default_playlists", [])
                    pid = data["playlist_id"]
                    if data.get("value") and pid not in ds:
                        ds.append(pid)
                    elif not data.get("value") and pid in ds:
                        ds.remove(pid)
                profile = update_profile(data["profile_id"], _default)
                return self._json(profile_brief(profile))
            if path == "/api/playlists/video":
                profile = find_profile(data["profile_id"])
                client = get_client(profile)
                video_id = eng.extract_video_id(str(data.get("link", "")))
                if not video_id:
                    raise ValueError("bad video link")
                added = 0
                for pl_id in data.get("playlist_ids", []):
                    try:
                        eng.add_video_to_playlist(client, video_id, pl_id)
                        added += 1
                    except Exception:
                        pass
                return self._json({"ok": True, "added": added})
            if path == "/api/providers/save":
                reg = eng.load_provider_registry()
                entry = data["entry"]
                if entry.get("id") in {p["id"] for p in reg["providers"]}:
                    for index, old in enumerate(reg["providers"]):
                        if old["id"] == entry["id"]:
                            reg["providers"][index] = entry
                else:
                    entry["id"] = entry.get("id") or eng.profile_slug(
                        entry["name"], {p["id"] for p in reg["providers"]})
                    reg["providers"].append(entry)
                    reg.setdefault("active", entry["id"])
                eng.save_provider_registry(reg)
                return self._json(reg)
            if path == "/api/providers/activate":
                reg = eng.load_provider_registry()
                if data.get("backup"):
                    reg["backup"] = data["id"] if reg.get("active") != data["id"] else None
                else:
                    reg["active"] = data["id"]
                eng.save_provider_registry(reg)
                return self._json(reg)
            if path == "/api/providers/delete":
                reg = eng.load_provider_registry()
                reg["providers"] = [p for p in reg["providers"] if p["id"] != data["id"]]
                if reg.get("active") == data["id"] and reg["providers"]:
                    reg["active"] = reg["providers"][0]["id"]
                if reg.get("backup") == data["id"]:
                    reg["backup"] = None
                eng.save_provider_registry(reg)
                return self._json(reg)
            if path == "/api/providers/models":
                return self._json({"models": eng.fetch_local_models(data.get("base_url", ""))})
            if path == "/api/parallel":
                config = eng.load_local_llm_config()
                raw = data.get("value", "auto")
                config["max_parallel_languages"] = "auto" if raw == "auto" else int(raw)
                eng.save_json_file("local_llm.json", config)
                return self._json({"ok": True})
            if path == "/api/presets/save":
                name = str(data.get("name", "")).strip()
                if name:
                    presets = eng._ui.setdefault("language_presets", {})
                    presets[name] = sorted(set(eng.get_profile_languages(find_profile(data["profile_id"]))))
                    eng.save_ui_settings()
                return self._json({"ok": True})
            if path == "/api/presets/delete":
                eng._ui.setdefault("language_presets", {}).pop(data.get("name"), None)
                eng.save_ui_settings()
                return self._json({"ok": True})
            if path == "/api/presets/apply":
                codes = eng._ui.get("language_presets", {}).get(data.get("name"), [])
                if codes:
                    update_profile(data["profile_id"], lambda p: p.__setitem__("languages", sorted(codes)))
                return self._json({"ok": True})
            return self._json({"error": "not found"}, 404)
        except Exception as error:
            self._json({"error": str(error)}, 400)

    def _file(self, name):
        full = os.path.abspath(os.path.join(STATIC_DIR, name))
        if not full.startswith(os.path.abspath(STATIC_DIR)) or not os.path.isfile(full):
            return self._json({"error": "not found"}, 404)
        with open(full, "rb") as f:
            body = f.read()
        ext = os.path.splitext(full)[1]
        self._send(200, body, MIME.get(ext, "application/octet-stream"))

    # --- API parts that need several engine calls ---

    def api_bootstrap(self):
        profiles = [profile_brief(p) for p in eng.load_channel_profiles()["profiles"]]
        reg = eng.load_provider_registry()
        config = eng.load_local_llm_config()
        provider = reg.get("active")
        provider = next((p for p in reg["providers"] if p["id"] == provider), None)
        self._json({
            "ui": {k: eng._ui.get(k) for k in
                   ("language", "user_name", "ask_playlists", "ask_schedule",
                    "language_presets", "web_active_profile", "ui_tr_mode", "ui_tr_type",
                    "ui_tr_source", "ui_tr_parts", "ui_add_defaults", "ui_sched")},
            "profiles": profiles,
            "secrets_found": bool(eng.find_secrets_files()),
            "providers": reg,
            "provider_online": bool(provider and provider.get("auth")),
            "parallel": config.get("max_parallel_languages", "auto"),
            "catalog": eng.available_language_catalog(),
            "series": eng.load_series_names(),
        })

    def api_job(self):
        job = None
        for candidate in sorted(JOBS.values(), key=lambda j: j["id"], reverse=True):
            job = candidate
            break
        if job is None:
            return self._json({"running": False, "done": False, "langs": {}, "log": []})
        with _LOCK:
            snapshot = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
                        for k, v in job.items()}
        self._json(snapshot)


def main():
    eng.restore_ui_settings()
    sys_stdout = __import__("sys").stdout
    import sys
    sys.stdout = _JobTee(sys_stdout)

    server = None
    for port in PORT_RANGE:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Все порты 8765–8789 заняты.")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"\n🌐 Веб-интерфейс: {url}  (закрытие — Ctrl+C здесь или кнопка в меню)")
    threading.Timer(0.6, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nПока!")


if __name__ == "__main__":
    main()
