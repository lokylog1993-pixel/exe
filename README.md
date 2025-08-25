# BitD GM AI (Локальный ведущий для «Клинков во Тьме»)

Локальный ИИ-ведущий (ГМ) для кампаний **Клинки во Тьме**. Работает офлайн через `llama-cpp-python`
(с GGUF-моделью) или онлайн через OpenAI-совместимый API. Русский язык по умолчанию.

## Возможности
- **Строгая роль ГМа**: модель ведёт игру, не раскрывая спойлеров и не выходит из роли.
- **Механики BitD**: экшн-роллы, позиция/эффект, крит/частичный/провал; сопротивление, engagement; часы.
- **Дайсы и состояние**: честные броски на стороне сервера; JSON-состояние кампании.
- **UI**: расширенный веб-интерфейс на Gradio: часы, Heat/Rep/Wanted/Coin, ручные броски.
- **Тюнинг**: подготовка датасета для SFT на базе ваших логов (`training/prepare_dataset.py`).

## Быстрый старт (локальный LLM)
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Скачайте **GGUF** модель (например, Llama 3.1 8B Instruct) и укажите путь в `.env`:
   ```env
   LLM_BACKEND=llama_cpp
   LLAMA_MODEL_PATH=/abs/path/to/model.gguf
   LLAMA_CTX_SIZE=4096
   LLAMA_MAX_TOKENS=800
   ```
3. Запустите сервер:
   ```bash
   python -m app.server
   ```
4. Откройте UI:
   ```bash
   python -m app.ui
   ```

## Быстрый старт (OpenAI-совместимый)
1. Заполните `.env`:
   ```env
   LLM_BACKEND=openai
   OPENAI_API_KEY=sk-...
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_MAX_TOKENS=800
   ```
2. Запуск как выше.

## CLI
```bash
bitd-gm chat
```

## Структура
- `app/server.py` — FastAPI сервер (`/chat`, `/state`, `/roll/*`, `/clock/*`, `/state/update`).
- `app/gm_agent.py` — оркестратор диалогов и вызовов «инструментов». Авто-наполнение часов, если модель указала `target_clock`.
- `app/tools.py` — кубики, часы, механики BitD.
- `app/prompts.py` — системный промпт на русском.
- `app/state.py` — JSON-хранилище состояния (coin/rep/heat/wanted/часы).
- `app/ui.py` — расширенный Gradio-интерфейс.
- `training/prepare_dataset.py` — сбор датасета из логов для SFT.
- `training/sft_train.py` — подсказки по fine-tuning.

## Логи
Каждый обмен сохраняется в `data/logs/chat.jsonl` для последующего обучения.

## Юр-вопросы
Не содержит правил из книги. Добавляйте **свои краткие конспекты** в `app/rules_summaries.md`.
