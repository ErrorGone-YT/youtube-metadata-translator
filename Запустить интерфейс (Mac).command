#!/bin/bash
cd "$(dirname "$0")"
python3 gui_app.py || { echo; read -p "Программа завершилась с ошибкой. Нажми Enter, чтобы закрыть окно..."; }
