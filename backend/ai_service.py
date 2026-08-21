"""Сервисный слой: интеграция с OpenAI для генерации задач и скрытого ИИ-аудита.

При отсутствии OPENAI_API_KEY используется детерминированный мок-режим,
чтобы проект оставался запускаемым без внешних зависимостей.
"""
import json
import os
import re
import uuid

from openai import AsyncOpenAI

from prompt_templates import SYSTEM_AI_JUDGE, SYSTEM_TASK_GENERATOR
from schemas import AIJudgeResponse, TaskGeneratorResponse

# ─── Локализация генерации задач под язык интерфейса ───
_LANG_DIRECTIONS = {"ru": "Russian", "en": "English", "de": "German"}

_LOC = {
    "ru": {
        "question": "Перед вами фрагмент FastAPI-приложения, обрабатывающего запросы к PostgreSQL. Тема: {topic}. Сложность: {difficulty}. Найдите критическую проблему производительности, которая может привести к деградации сервиса под нагрузкой.",
        "options": [
            "Утечка соединений в context manager",
            "CPU-bound blocking call в async-эндпоинте",
            "Отсутствие миграций базы данных",
            "Некорректная обработка CORS",
        ],
        "explanation": "Вызов блокирующего CPU-кода (например, time.sleep или тяжёлых синхронных вычислений) внутри async-функции блокирует весь event loop, поэтому производительность падает до одного запроса за раз.",
    },
    "en": {
        "question": "You are reviewing a FastAPI application that queries PostgreSQL. Topic: {topic}. Difficulty: {difficulty}. Find the critical performance issue that could degrade the service under load.",
        "options": [
            "Connection leak in a context manager",
            "CPU-bound blocking call in an async endpoint",
            "Missing database migrations",
            "Incorrect CORS handling",
        ],
        "explanation": "A blocking CPU-bound call (e.g. time.sleep or heavy synchronous computation) inside an async function blocks the entire event loop, so throughput drops to one request at a time.",
    },
    "de": {
        "question": "Sie prüfen eine FastAPI-Anwendung, die PostgreSQL abfragt. Thema: {topic}. Schwierigkeit: {difficulty}. Finden Sie das kritische Performance-Problem, das den Dienst unter Last beeinträchtigen kann.",
        "options": [
            "Verbindungsleck im Context-Manager",
            "Blockierender CPU-Aufruf in einem async-Endpunkt",
            "Fehlende Datenbankmigrationen",
            "Fehlerhafte CORS-Verwaltung",
        ],
        "explanation": "Ein blockierender CPU-Aufruf (z. B. time.sleep oder schwere synchrone Berechnungen) innerhalb einer async-Funktion blockiert die gesamte Event-Loop, sodass der Durchsatz auf eine Anfrage gleichzeitig sinkt.",
    },
}


class AIService:
    def __init__(self) -> None:
        self.api_key: str | None = os.getenv("OPENAI_API_KEY")
        self.model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

        # Кэш сгенерированных задач: (topic, difficulty, language) → TaskGeneratorResponse.
        # Повторные запросы по одному и тому же стеку — мгновенно из кэша.
        self._task_cache: dict = {}

    async def generate_task(
        self, topic: str, difficulty: str, language: str = "ru"
    ) -> TaskGeneratorResponse:
        """Генерация задачи. OpenAI → мок (если ключа нет).

        language — код языка интерфейса (ru/en/de), задание переводится под него.
        """
        cache_key = f"{topic}|{difficulty}|{language}"
        cached = self._task_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self._openai_generate_task(topic, difficulty, language)
        if result is None:
            result = self._mock_task(topic, difficulty, language)

        self._task_cache[cache_key] = result
        return result

    async def _openai_generate_task(
        self, topic: str, difficulty: str, language: str
    ) -> TaskGeneratorResponse | None:
        if self.client is None:
            return None
        lang_name = _LANG_DIRECTIONS.get(language, "Russian")
        user_prompt = (
            f"Generate a unique engineering challenge for the technology/topic: {topic}.\n"
            f"Difficulty: {difficulty}.\n"
            f"ALL text fields (question_text, options, explanation, visual labels) MUST be written in {lang_name}.\n"
            "Return only valid JSON."
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_TASK_GENERATOR},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return TaskGeneratorResponse(**data)
        except Exception:
            return None

    async def judge_prompt(self, user_prompt: str, session_context: dict) -> AIJudgeResponse:
        if self.client is None:
            return self._mock_judge(user_prompt)

        user_content = (
            "Audit this user prompt for the AI assistant in a technical task.\n"
            f"Session context (JSON): {json.dumps(session_context, ensure_ascii=False)}\n"
            f"User prompt:\n{user_prompt}\n"
            "Return only valid JSON."
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_AI_JUDGE},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return AIJudgeResponse(**data)
        except Exception:
            return self._mock_judge(user_prompt)

    # ─── Детерминированный мок-режим (работоспособен без ключа OpenAI) ───
    def _mock_task(
        self, topic: str, difficulty: str, language: str = "ru"
    ) -> TaskGeneratorResponse:
        loc = _LOC.get(language, _LOC["ru"])
        options = loc["options"]
        return TaskGeneratorResponse(
            task_id=str(uuid.uuid4()),
            topic=topic,
            difficulty=difficulty,
            question_text=loc["question"].format(topic=topic, difficulty=difficulty),
            visual_specification={
                "type": "svg_code",
                "content": (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">'
                    '<rect width="400" height="200" fill="#1e1e2e"/>'
                    '<text x="20" y="40" fill="#cdd6f4" font-size="14" font-family="monospace">'
                    "async client → await db.execute()</text>"
                    '<circle cx="200" cy="140" r="25" fill="#f38ba8"/>'
                    '<text x="182" y="146" fill="#1e1e2e" font-size="16">!</text>'
                    "</svg>"
                ),
            },
            options=options,
            correct_answer=options[1],
            explanation=loc["explanation"],
        )

    def _mock_judge(self, user_prompt: str) -> AIJudgeResponse:
        text = user_prompt.lower()
        # Эвристика «глубины»: уточняющие вопросы, декомпозиция, факт-чекинг
        depth_markers = ["?", "уточн", "декомпоз", "риск", "план", "шаг", "провер", "баг", "ограничен"]
        craft_markers = ["нужно", "требуется", "сделай", "реализуй", "исправь", "напиши", "создай", "критери"]

        depth_hits = sum(1 for m in depth_markers if m in text)
        craft_hits = sum(1 for m in craft_markers if m in text)

        base = 0.55
        craft = min(0.98, base + craft_hits * 0.08)
        depth = min(0.98, base + depth_hits * 0.07)

        return AIJudgeResponse(
            prompt_craft_score=round(craft, 2),
            process_depth_score=round(depth, 2),
            analysis={
                "strengths": (
                    "Чёткие формулировки, структура запроса прослеживается."
                    if craft_hits >= 2 else
                    "Запрос сформулирован, но можно добавить больше конкретики."
                ),
                "weaknesses": (
                    "Мало уточняющих вопросов и декомпозиции задачи."
                    if depth_hits < 2 else
                    "Хорошая декомпозиция, однако недостаточно явного факт-чекинга."
                ),
            },
        )

    # ─── Чат с моделью (OpenAI → мок) ───
    async def chat_reply(self, message: str, context: str = "") -> str:
        """Ответ модели на сообщение пользователя: OpenAI → мок-ответ."""
        if self.client is not None:
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Ты — ИИ-ассистент для технического интервью. Отвечай кратко и по делу."},
                        {"role": "user", "content": message},
                    ],
                    temperature=0.7,
                    max_tokens=512,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                pass

        return self._mock_chat(message)

    def _mock_chat(self, message: str) -> str:
        text = message.lower()
        if any(m in text for m in ["шаг", "план", "декомпоз"]):
            return "Отличная декомпозиция! Рекомендую: 1) уточнить требования, 2) выделить MVP, 3) проверить на галлюцинации ИИ, 4) зафиксировать критерии приёмки."
        if any(m in text for m in ["баг", "ошибк", "bug"]):
            return "Проверьте: 1) пагинацию (нет лимита), 2) уникальность email, 3) обработку 404/422, 4) блокирующие вызовы в async-функциях."
        if any(m in text for m in ["галюцин", "галлюцин", "hallucin"]):
            return "Критически важно! Попросите модель обосновать каждое утверждение и сверьте с реальной задачей клиента. Не доверяйте стек из «14 блокчейнов» без факт-чекинга."
        return "Понял. Уточните пожалуйста: 1) какова бизнес-цель? 2) какие ограничения (время, бюджет, стек)? 3) кто конечные пользователи?"

    def chat_status(self) -> dict:
        """Синхронный статус (для эндпоинта /api/chat/status)."""
        return {
            "available": bool(self.client),
            "provider": "openai" if self.client else "mock",
            "model": self.model if self.client else "mock",
        }


ai_service = AIService()