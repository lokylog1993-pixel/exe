
# BitD GM AI — Настольное приложение

Этот пакет запускается как **нативное окно**, внутри которого открывается интерфейс (Gradio) и локальный API (FastAPI).

## Быстрый старт (без сборки)
```bash
pip install -r requirements.txt
python run_app.py
```
Откроется окно «BitD GM AI». Состояние пишется в `~/.bitd_gm_ai/state.json` (можно поменять переменной `BITD_STATE_PATH`).

## Сборка в одиночный исполняемый файл (PyInstaller)
### Windows
```bat
packaging\build_windows.bat
```
Готовый EXE лежит в `dist\BitD_GM_AI\BitD GM AI.exe`.

### macOS
```bash
chmod +x packaging/build_macos.command
packaging/build_macos.command
```
Бандл будет в `dist/BitD_GM_AI/` (можно запустить двукликом).

### Linux
```bash
chmod +x packaging/build_linux.sh
packaging/build_linux.sh
```

> Примечания:
> - Если окно не открывается, убедитесь, что установлен **pywebview** и на Linux — бэкенд WebKit/GTK (обычно `sudo apt install python3-webview gir1.2-webkit2-4.0`).
> - PDF экспорт карточек требует `reportlab` (`pip install reportlab`).

## Порты
- API (FastAPI): `127.0.0.1:8000`
- UI (Gradio): `127.0.0.1:7860`

## Данные
По умолчанию состояние хранится в `~/.bitd_gm_ai/state.json` (чтобы сборка была переносимой). Можно задать:
```bash
export BITD_STATE_PATH="/путь/к/state.json"
```

Приятной игры!
