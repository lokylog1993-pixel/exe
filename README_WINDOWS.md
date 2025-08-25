
# BitD GM AI — Windows сборка

## Запуск без сборки
1. Установите Python 3.10+.
2. Откройте PowerShell/Command Prompt в папке проекта.
3. Выполните:
   ```bat
   pip install -r requirements.txt
   python run_app.py
   ```

## Сборка EXE (PyInstaller)
1. Запустите:
   ```bat
   packaging\build_windows.bat
   ```
2. Готовый exe лежит в `dist\BitD_GM_AI\BitD GM AI.exe`.
3. (Опционально) Создайте ярлык на рабочем столе:
   ```powershell
   powershell -ExecutionPolicy Bypass -File packaging\create_shortcut.ps1
   ```

### Примечания
- Для нативного окна используется **pywebview**. На Windows рекомендован движок *Edge (WebView2)* — он используется автоматически (если установлен). Иначе откроется браузер.
- Состояние по умолчанию: `%USERPROFILE%\.bitd_gm_ai\state.json` (меняется переменной `BITD_STATE_PATH`).
- PDF экспорт требует `reportlab`:
  ```bat
  pip install reportlab
  ```
