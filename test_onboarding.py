"""Onboarding smoke tests. Run from the repo root: python test_onboarding.py

All file operations are redirected to a temporary data directory, so the real
data/ folder (keys, tokens, profiles) is never touched.
"""
import importlib.util
import builtins
import io
import contextlib
import json
import os
import shutil
import tempfile

spec = importlib.util.spec_from_file_location("ytt", "yt_metadata_translator.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

TMP = tempfile.mkdtemp(prefix="ytt_test_data_")
m.DATA_DIR = TMP  # isolate: every read/write goes to the temp folder


def clean():
    for f in os.listdir(TMP):
        path = os.path.join(TMP, f)
        os.remove(path) if os.path.isfile(path) else shutil.rmtree(path)


def run(answers):
    m._ui["language"] = None
    m._ui["user_name"] = ""
    it = iter(answers)
    builtins.input = lambda *a, **k: next(it)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.main()
    return buf.getvalue()


# TEST 1: uk first run, no secrets -> skip -> restricted menu -> settings -> exit
clean()
out = run(["2", "Майстро", "0", "1", "0", "0", "0"])
assert "Виберіть мову інтерфейсу" in out
assert "Не знайдено файл client_secrets" in out
assert "README.uk.md" in out and "console.cloud.google.com" in out
assert "Вітаю, Майстро! Що робитимемо?" in out
assert "Налаштування ще не завершено" in out
assert "Мова інтерфейсу" in out  # settings opened
assert json.load(open(os.path.join(TMP, "ui_settings.json"), encoding="utf-8")) == {
    "ui_language": "uk", "user_name": "Майстро"}
print("TEST 1 OK: uk onboarding, secrets screen with links, restricted menu")

# TEST 2: relaunch — no onboarding repeat
out = run(["0", "0"])
assert "Виберіть мову інтерфейсу" not in out
assert "Вітаю, Майстро" in out
print("TEST 2 OK: no re-onboarding")

# TEST 3: ru fresh + 3 secrets files -> wizard (no playlist question) -> graceful auth failure
clean()
for f in ("a", "b", "c"):
    open(os.path.join(TMP, f"client_secrets_{f}.json"), "w").write("{}")
out = run(["3", "Тестовый юзер", "Профіль Тест", "2", "", "0"])
assert "Выберите язык интерфейса" in out
assert "Который из файлов ключей твой?" in out
assert "Профиль 'Профіль Тест' создан" in out
assert "ID плейлиста" not in out, "playlist question should not be asked"
assert "Ошибка авторизации" in out  # fake secrets rejected, script survives
profiles = json.load(open(os.path.join(TMP, "channel_profiles.json"), encoding="utf-8"))
assert profiles["profiles"][0]["client_secrets_file"] == "client_secrets_b.json"
assert profiles["profiles"][0]["display_name"] == "Профіль Тест"
assert profiles["profiles"][0]["playlist_id"] == ""
saved = json.load(open(os.path.join(TMP, "ui_settings.json"), encoding="utf-8"))
assert saved == {"ui_language": "ru", "user_name": "Тестовый юзер"}
print("TEST 3 OK: ru wizard, multi-secrets pick, no playlist question, graceful auth failure")

# TEST 4: relaunch with profile — select list, 0 exits cleanly
out = run(["0", "0"])
assert "Твои профили каналов" in out and "Профіль Тест" in out
print("TEST 4 OK: profile list shown, exit works")

shutil.rmtree(TMP)
print("ALL TESTS PASSED")
