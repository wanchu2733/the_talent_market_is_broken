# No-Resume Skill Market — Backend (FastAPI)

Production-ready модуль динамической верификации, онлайн-промптинга и геймифицированного тестирования.

## Функциональность

- **Генерация уникальных задач** через OpenAI (SVG-спецификации, matplotlib-скрипты, image-промпты)
- **Скрытый ИИ-аудит** промптов кандидата (формула 50 / 25 / 25)
- **Жёсткая дедупликация** SHA-256 для промптов и решений ИИ (unique_prompts, unique_solutions)
- **SLA-лимиты** по сложности задачи (время + вложенность диалога)
- **Валидация Pydantic v2** (TaskGeneratorResponse, AIJudgeResponse)
- **Docker / docker-compose** с PostgreSQL 15 и healthcheck
- **Режим без ключа OpenAI** — детерминированный мок (для локальной разработки)
- **Локальная LLM через Ollama** — чат с ИИ-ассистентом полностью офлайн (без OpenAI)
- **Сбор профиля по email** — GitHub API: email → репозитории → языки/темы → карта навыков

## Быстрый запуск (Docker)

```bash
# 1. Перейти в папку backend
cd Platform/backend

# 2. Скопировать переменные окружения
cp .env.example .env
# По желанию вписать OPENAI_API_KEY

# 3. Запуск
docker compose up --build
```

- API: http://localhost:8000
- Документация Swagger: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health

## Локальный запуск (без Docker, mock-режим)

```bash
cd Platform/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload --port 8000
```

## Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/session/start?user_id=1&topic=FastAPI&difficulty=medium` | Создание сессии + генерация задачи |
| POST | `/prompt/send` | Отправка промпта кандидата (дедупликация SHA-256 + скрытый аудит) |
| POST | `/session/submit` | Завершение сессии и расчёт финального балла |
| GET | `/session/{session_id}/analytics` | Внутренняя аналитика для HR (скрытые метрики) |
| GET | `/health` | Healthcheck |
| GET | `/api/chat/status` | Статус ИИ-модели для чата (online/offline) |
| POST | `/api/chat/send` | Чат с моделью (Ollama локально / OpenAI) |
| POST | `/api/profile/load` | Сбор навыков кандидата по email через GitHub API |

## Пример запроса

```bash
# Старт сессии
curl -X POST "http://localhost:8000/session/start?user_id=1&topic=FastAPI&difficulty=medium"

# Отправка промпта (подставьте session_id из ответа)
curl -X POST "http://localhost:8000/prompt/send" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "user_prompt": "Уточни требования и разложи задачу на шаги"}'

# Завершение сессии (correct_answer скрыт, получите его из внутренней аналитики)
curl -X POST "http://localhost:8000/session/submit" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "selected_answer": "CPU-bound blocking call в async-эндпоинте"}'
```

## Структура

```
backend/
├── app.py               # FastAPI-приложение, маршруты, формула 50/25/25
├── ai_service.py        # OpenAI-интеграция + детерминированный mock
├── database.py          # Async SQLAlchemy engine / сессии
├── models.py            # SQLAlchemy-модели (companies, users, test_sessions, ...)
├── schemas.py           # Pydantic v2 схемы валидации
├── prompt_templates.py  # Системные промпты (генератор задач, ИИ-судья)
├── requirements.txt
├── Dockerfile           # Multi-stage сборка (python:3.11-slim)
└── docker-compose.yml   # PostgreSQL 15 + API
```

## Формула итогового балла

```
Final Score = ((Task Score × 0.50) + (Prompt Craft × 0.25) + (Process Depth × 0.25))
              × Modifier_time × Modifier_depth
```

- **Modifier_time** — штраф за превышение SLA лимита (мин. 0.4)
- **Modifier_depth** — поощрение осмысленной вложенности промптов
- Prompt Craft и Process Depth **скрыты** от кандидата (видны только HR через `/analytics`)

## Локальная LLM для чата (Ollama)

Чат с ИИ-ассистентом работает **без OpenAI** — через локальную модель Ollama.

```bash
# 1. Установить и запустить Ollama + модель (скрипт делает всё автоматически)
cd Platform/backend
./setup_local_model.sh

# 2. Перезапустить бэкенд
.venv/bin/uvicorn app:app --reload --port 8000
```

После этого `/api/chat/status` вернёт:
```json
{"available": true, "provider": "ollama", "model": "llama3.1"}
```

Переменные окружения (опционально):
- `OLLAMA_BASE_URL` — адрес Ollama (по умолчанию `http://localhost:11434`)
- `OLLAMA_MODEL` — имя модели (по умолчанию `llama3.1`)
- `GITHUB_TOKEN` — токен GitHub для расширенного лимита API при сборе профиля

## Сбор профиля по email

```bash
# Сбор навыков кандидата по email через GitHub API
curl -X POST "http://localhost:8000/api/profile/load" \
  -H "Content-Type: application/json" \
  -d '{"email": "developer@github.com"}'
```

Ответ:
```json
{
  "email": "developer@github.com",
  "github_username": "devuser",
  "skills": ["python", "fastapi", "docker", "kubernetes", "sql"],
  "source": "github",
  "repos_found": 12
}
```

Если GitHub не найден — используется эвристика по локальной части email.

## Чат с моделью

```bash
# Статус модели
curl http://localhost:8000/api/chat/status

# Отправка сообщения в чат
curl -X POST "http://localhost:8000/api/chat/send" \
  -H "Content-Type: application/json" \
  -d '{"message": "Как разложить задачу на этапы?", "context": "FastAPI"}'
```
