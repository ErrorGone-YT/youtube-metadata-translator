"""Smoke test for the wired main menu flows (isolated temp data dir)."""
import importlib.util
import builtins
import io
import contextlib
import json
import os
import tempfile
import shutil

spec = importlib.util.spec_from_file_location("ytt", "yt_metadata_translator.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m._ui["language"] = "ru"
TMP = tempfile.mkdtemp()
m.DATA_DIR = TMP

# fake YouTube service
class FakeTube:
    def __init__(self):
        self.updates = []
        self.inserts = []
        self.mode = None
    def videos(self):
        self.mode = "videos"
        return self
    def playlistItems(self):
        self.mode = "playlistItems"
        return self
    def list(self, **kw): return self
    def update(self, **kw):
        self.updates.append(kw)
        return self
    def insert(self, **kw):
        self.inserts.append(kw)
        return self
    def execute(self):
        if self.mode == "videos":
            self.mode = None
            return {"items": [{"id": VIDEO_ID,
                               "snippet": {"tags": [], "categoryId": "22"},
                               "localizations": {}}]}
        return {}

youtube = FakeTube()

# channel with one video; profile with languages + defaults
json.dump({"ui_language": "ru", "user_name": "Командир"},
          open(os.path.join(TMP, "ui_settings.json"), "w", encoding="utf-8"))
os.makedirs(os.path.join(TMP, "profiles", "test"))
open(os.path.join(TMP, "profiles", "test", "calendar.json"), "w").write("{}")
open(os.path.join(TMP, "profiles", "test", "token.pickle"), "w").write("x")
open(os.path.join(TMP, "client_secrets_test.json"), "w").write("{}")
json.dump({"profiles": [{"profile_id": "test", "display_name": "Тест", "channel_id": "c",
    "channel_title": "Тестовый канал", "token_file": "profiles/test/token.pickle",
    "client_secrets_file": "client_secrets_test.json",
    "playlists": [{"id": "PLdef123456789", "name": "Основной"}],
    "default_playlists": ["PLdef123456789"],
    "languages": ["de", "ja"],
    "publ_calendar_file": "profiles/test/calendar.json"}]},
    open(os.path.join(TMP, "channel_profiles.json"), "w", encoding="utf-8"))

VIDEO_ID = "abc12345678"
SHORT_ID = "shortvid001"
m.get_channel_videos = lambda yt: ([
    {"snippet": {"resourceId": {"videoId": VIDEO_ID}, "publishedAt": "2026-10-01T10:00:00Z",
                 "title": "My latest long"}}
], {VIDEO_ID: 120.0})
m.get_channel_videos_all = lambda yt: ([
    {"snippet": {"resourceId": {"videoId": VIDEO_ID}, "publishedAt": "2026-10-01T10:00:00Z",
                 "title": "My latest long"}},
    {"snippet": {"resourceId": {"videoId": SHORT_ID}, "publishedAt": "2026-10-02T10:00:00Z",
                 "title": "My short"}}
], {VIDEO_ID: 120.0, SHORT_ID: 30.0})
m.fetch_video_source_metadata = lambda yt, vid: {
    "title": "Fresh title", "description": "Fresh description with\n\nblank line"}
captured = {}
def fake_localize(metadata, langs, parts=("title", "description")):
    captured.update(metadata=metadata, langs=langs, parts=parts)
    json.dump({code: {"title": f"T {code}", "description": f"D {code}" if "description" in parts else metadata["description"]} for code in langs},
              open(os.path.join(TMP, "localizations.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
m.localize_metadata_via_llm = fake_localize
_orig_translate_one = m._translate_one

def run(answers):
    it = iter(answers)
    builtins.input = lambda *a, **k: next(it)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.profile_menu({"profile_id": "test", "display_name": "Тест", "channel_title": "Тестовый канал",
                        "token_file": "profiles/test/token.pickle",
                        "client_secrets_file": "client_secrets_test.json",
                        "playlists": [{"id": "PLdef123456789", "name": "Основной"}],
                        "default_playlists": ["PLdef123456789"],
                        "languages": ["de", "ja"],
                        "publ_calendar_file": "profiles/test/calendar.json"},
                       {"profiles": []}, youtube)
    return buf.getvalue()

# 1) Translation: translate actual data -> update -> add to defaults -> no schedule
out = run(["1", "1", "1", "1", "1", "д", "н", "0", "0", "0", "0"])
assert "Последнее видео" in out and "Fresh title" in out
assert captured["langs"] == ["de", "ja"]
assert "Перевожу на 2 языков" in out
assert len(youtube.updates) == 1 and youtube.updates[0]["body"]["snippet"]["title"] == "Fresh title"
assert "Видео abc12345678 обновлено" in out
assert len(youtube.inserts) == 1 and "PLdef123456789" in str(youtube.inserts[0])
print("TRANSLATION FLOW OK")

# 2) Playlists: add a video link to the defaults
youtube.inserts.clear()
out = run(["2", "https://youtu.be/xyz789abcde", "н", "0"])
assert "Основной — PLdef123456789" in out
assert len(youtube.inserts) == 1 and "xyz789abcde" in str(youtube.inserts[0])
print("PLAYLIST FLOW OK")

# 3) Deferred publishing: link + date (2026-11-01 is a Sunday, allowed)
out = run(["3", "https://youtu.be/xyz789abcde", "011126", "н", "0"])
assert "выйдет" in out and "01.11.2026" in out
assert youtube.updates[-1]["body"]["status"]["publishAt"].startswith("2026-11-01")
print("SCHEDULE FLOW OK")

# 4) gating: without languages the Translation item explains what to do
profile_no_langs = {"profile_id": "test", "display_name": "Тест", "channel_title": "Тестовый канал",
                    "token_file": "profiles/test/token.pickle",
                    "client_secrets_file": "client_secrets_test.json",
                    "playlists": [], "default_playlists": [], "languages": [],
                    "publ_calendar_file": "profiles/test/calendar.json"}
out = run.__wrapped__ if False else None
it = iter(["1", "0"])
builtins.input = lambda *a, **k: next(it)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m.profile_menu(profile_no_langs, {"profiles": []}, youtube)
out = buf.getvalue()
assert "Не выбраны языки перевода" in out and "1) Перевод" in out
print("GATING OK")

# 5) no defaults -> playlist flow explains where to set them
out = run.__wrapped__ if False else None
it = iter(["2", "0"])
builtins.input = lambda *a, **k: next(it)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m.profile_menu(profile_no_langs, {"profiles": []}, youtube)
out = buf.getvalue()
assert "Плейлисты по умолчанию не выбраны" in out
print("NO-DEFAULTS WARN OK")


# 6) batch modes: all longs and all shorts, picked by duration
fetched = []
def fake_translate_one(yt, profile, vid, context=None, parts=None, ask_source=True):
    fetched.append(vid)
    return True
m._translate_one = fake_translate_one
m.get_channel_videos = lambda yt: m.get_channel_videos_all(yt)

out = run(["1", "3", "1", "д", "1", "0", "0", "0", "0"])
assert fetched == [VIDEO_ID], fetched
fetched.clear()
out = run(["1", "3", "2", "д", "1", "0", "0", "0", "0"])
assert fetched == [SHORT_ID], fetched
print("BATCH LONG/SHORT OK")

# 7) last short
out = run(["1", "1", "2", "1", "1", "н", "н", "0", "0", "0", "0"])
assert fetched[-1] == SHORT_ID
print("LAST SHORT OK")

# restore the real _translate_one after the batch mocks
m._translate_one = _orig_translate_one


# 8) titles-only: description stays the source text after merge
captured.clear()
out = run(["1", "1", "1", "2", "1", "н", "н", "0", "0", "0", "0"])
print("CAPTURED:", captured)
print(out)
assert captured["parts"] == ("title",)
locs = json.load(open(os.path.join(TMP, "localizations.json"), encoding="utf-8"))
assert locs["de"]["title"] == "T de"
assert locs["de"]["description"] == "Fresh description with\n\nblank line"
print("TITLES-ONLY MERGE OK")

# 9) switch profile returns "switch"
it = iter(["5", "0"])
builtins.input = lambda *a, **k: next(it)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    result = m.profile_menu({"profile_id": "test", "display_name": "Тест", "channel_title": "Тестовый канал",
                             "token_file": "profiles/test/token.pickle",
                             "client_secrets_file": "client_secrets_test.json",
                             "playlists": [], "default_playlists": [], "languages": ["de"],
                             "publ_calendar_file": "profiles/test/calendar.json"},
                            {"profiles": []}, youtube)
assert result == "switch", result
assert "Сменить профиль" in buf.getvalue()
print("SWITCH PROFILE OK")

shutil.rmtree(TMP)
print("ALL MENU TESTS PASSED")
