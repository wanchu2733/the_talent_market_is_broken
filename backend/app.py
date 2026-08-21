import hashlib
import json
import datetime
import uuid
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from database import get_db, init_db
import models
import schemas
from ai_service import ai_service
import profile_service


app = FastAPI(
    title="No-Resume Dynamic Skill & Verification Engine API",
    description="Онлайн-промптинг, геймифицированные тесты и скрытый ИИ-аудит (50 / 25 / 25)",
    version="2.0.0",
)

# Загрузка переменных окружения из .env
load_dotenv(Path(__file__).resolve().parent / ".env")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация SLA-лимитов по сложности (из финального ТЗ)
DIFFICULTY_LIMITS = {
    "easy": {"max_seconds": 600, "max_depth": 2, "nest_factor": 1.0},
    "medium": {"max_seconds": 1200, "max_depth": 4, "nest_factor": 1.5},
    "hard": {"max_seconds": 2100, "max_depth": 7, "nest_factor": 2.2},
}

# In-memory fallback (когда PostgreSQL недоступен)
MEMORY_SESSIONS: Dict[int, Dict[str, Any]] = {}
MEMORY_COUNTER = 0
DB_AVAILABLE = True


@app.on_event("startup")
async def startup_event():
    global DB_AVAILABLE
    try:
        await init_db()
        DB_AVAILABLE = True
    except Exception as exc:  # БД может быть недоступна в first-start
        DB_AVAILABLE = False
        print(f"[startup] DB init skipped: {exc} — using in-memory fallback")


@app.get("/")
async def root():
    return {
        "service": "No-Resume Skill Market API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.datetime.utcnow().isoformat()}


# ─── Утилиты дедупликации ───

def hash_prompt(prompt_text: str) -> str:
    """Очищенный промпт в нижнем регистре → SHA-256 (жесткая дедупликация)."""
    cleaned = prompt_text.strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def hash_solution(ai_response: dict) -> str:
    """Сериализованный JSON со строго отсортированными ключами → SHA-256."""
    serialized = json.dumps(ai_response, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def get_or_create_unique_prompt(db: AsyncSession, prompt_text: str) -> models.UniquePrompt:
    prompt_hash = hash_prompt(prompt_text)
    stmt = insert(models.UniquePrompt).values(
        prompt_hash=prompt_hash,
        prompt_text=prompt_text,
    ).on_conflict_do_nothing(index_elements=["prompt_hash"])
    await db.execute(stmt)

    res = await db.execute(
        select(models.UniquePrompt).where(models.UniquePrompt.prompt_hash == prompt_hash)
    )
    return res.scalar_one()


async def get_or_create_unique_solution(db: AsyncSession, ai_response: dict) -> models.UniqueSolution:
    solution_hash = hash_solution(ai_response)
    stmt = insert(models.UniqueSolution).values(
        solution_hash=solution_hash,
        ai_response=ai_response,
    ).on_conflict_do_nothing(index_elements=["solution_hash"])
    await db.execute(stmt)

    res = await db.execute(
        select(models.UniqueSolution).where(models.UniqueSolution.solution_hash == solution_hash)
    )
    return res.scalar_one()


# ─── Эндпоинты ───

@app.post("/session/start", response_model=Dict[str, Any])
async def start_session(
    user_id: int,
    topic: str = "FastAPI Async Architecture",
    difficulty: str = "medium",
    language: str = "ru",
    db: AsyncSession = Depends(get_db),
):
    """Создание активной сессии + генерация уникальной задачи через ИИ/мок.

    language — язык интерфейса (ru/en/de), задача генерируется на этом языке.
    """
    global MEMORY_COUNTER
    generated = await ai_service.generate_task(topic=topic, difficulty=difficulty, language=language)

    limits = DIFFICULTY_LIMITS.get(generated.difficulty, DIFFICULTY_LIMITS["medium"])

    # Публичный ответ без correct_answer/explanation (скрытый аудит)
    public_task = generated.model_dump(exclude={"correct_answer", "explanation"})
    public_task["max_allowed_seconds"] = limits["max_seconds"]
    public_task["max_allowed_depth"] = limits["max_depth"]

    # Пытаемся сохранить в БД; если недоступна — in-memory fallback
    try:
        new_session = models.TestSession(
            user_id=user_id,
            status="active",
            internal_analytics={
                "current_task": generated.model_dump(),
                "sla_limits": limits,
                "prompt_history": [],
            },
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return {"session_id": new_session.id, "task": public_task}
    except Exception as exc:
        MEMORY_COUNTER += 1
        session_id = MEMORY_COUNTER
        MEMORY_SESSIONS[session_id] = {
            "user_id": user_id,
            "status": "active",
            "started_at": datetime.datetime.utcnow(),
            "internal_analytics": {
                "current_task": generated.model_dump(),
                "sla_limits": limits,
                "prompt_history": [],
            },
            "logs": [],
        }
        return {"session_id": session_id, "task": public_task}


@app.post("/prompt/send", response_model=Dict[str, Any])
async def send_user_prompt(payload: schemas.UserPromptRequest, db: AsyncSession = Depends(get_db)):
    """Отправка промпта пользователя: дедупликация SHA-256 + скрытый ИИ-аудит."""
    # 1. Проверка сессии
    res = await db.execute(
        select(models.TestSession).where(models.TestSession.id == payload.session_id)
    )
    session = res.scalar_one_or_none()
    if not session or session.status != "active":
        raise HTTPException(status_code=400, detail="Session not found or already closed")

    # 2. Текущий уровень вложенности (number of existing human logs + 1)
    count_res = await db.execute(
        select(func.count(models.PromptLog.id)).where(
            models.PromptLog.session_id == payload.session_id,
            models.PromptLog.author_type == "human",
        )
    )
    current_nesting = int(count_res.scalar_one()) + 1
    task_meta = session.internal_analytics.get("current_task", {})
    limits = session.internal_analytics.get("sla_limits") or DIFFICULTY_LIMITS["medium"]
    max_depth = limits["max_depth"]

    if current_nesting > max_depth:
        raise HTTPException(
            status_code=403,
            detail=f"Достигнут лимит вложенности промптов ({max_depth}) для текущей сложности",
        )

    # 3. Расчёт потраченных секунд на шаг
    now = datetime.datetime.utcnow()
    if current_nesting == 1:
        seconds_spent = max(1, int((now - session.started_at).total_seconds()))
    else:
        # Время с последнего human-лога (приближенно: берём из internal_analytics)
        history = session.internal_analytics.get("prompt_history", [])
        last_ts = history[-1].get("timestamp") if history else session.started_at.isoformat()
        try:
            last_dt = datetime.datetime.fromisoformat(last_ts)
        except Exception:
            last_dt = session.started_at
        seconds_spent = max(1, int((now - last_dt).total_seconds()))

    # 4. Дедупликация промпта
    unique_prompt = await get_or_create_unique_prompt(db, payload.user_prompt)

    # 5. Скрипт-генерация ответа ИИ (в проде — вызов копилота)
    ai_response = {
        "reply": "Понял задачу. Предлагаю следующий план: 1) уточнить требования, "
                 "2) разбить на подзадачи, 3) проверить на галлюцинации и баги.",
        "nesting_level": current_nesting,
        "suggested_steps": ["Декомпозиция", "Сбор уточняющих вопросов", "Факт-чекинг"],
    }

    # 6. Дедупликация решения
    unique_solution = await get_or_create_unique_solution(db, ai_response)

    # 7. Скрытый ИИ-аудит (Prompt Craft + Process Depth)
    judge_result = await ai_service.judge_prompt(
        payload.user_prompt,
        session_context={"topic": task_meta.get("topic"), "difficulty": task_meta.get("difficulty")},
    )

    # 8. Логирование шага
    new_log = models.PromptLog(
        session_id=payload.session_id,
        unique_prompt_id=unique_prompt.id,
        unique_solution_id=unique_solution.id,
        iteration_number=current_nesting,
        author_type="human",
        seconds_spent_on_step=seconds_spent,
        nesting_level=current_nesting,
        prompt_craft_score=judge_result.prompt_craft_score,
        process_depth_score=judge_result.process_depth_score,
        analysis_metrics=judge_result.analysis,
        tokens_used=180,
    )
    db.add(new_log)

    # 9. Обновляем историю сессии во внутренней аналитике
    history = session.internal_analytics.get("prompt_history", [])
    history.append({
        "iteration": current_nesting,
        "prompt_preview": payload.user_prompt[:200],
        "timestamp": now.isoformat(),
        "seconds_spent": seconds_spent,
    })
    session.internal_analytics["prompt_history"] = history
    db.add(session)
    await db.commit()

    return {
        "ai_response": ai_response,
        "nesting_level": current_nesting,
        "seconds_spent": seconds_spent,
        "remaining_depth": max(0, max_depth - current_nesting),
    }


@app.post("/session/submit", response_model=Dict[str, Any])
async def submit_session(payload: schemas.SubmitAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Завершение сессии: финальный балл по формуле (50 / 25 / 25) с модификаторами времени и глубины."""
    # In-memory fallback
    if payload.session_id in MEMORY_SESSIONS:
        mem = MEMORY_SESSIONS[payload.session_id]
        if mem["status"] != "active":
            raise HTTPException(status_code=400, detail="Session not found or already closed")

        task_data = mem["internal_analytics"].get("current_task", {})
        is_correct = task_data.get("correct_answer") == payload.selected_answer
        performance_score = 100.0 if is_correct else 0.0

        logs = mem.get("logs", [])
        has_logs = bool(logs)
        if has_logs:
            avg_craft = sum([l["prompt_craft_score"] for l in logs]) / len(logs) * 100
            avg_depth = sum([l["process_depth_score"] for l in logs]) / len(logs) * 100
        else:
            avg_craft = None
            avg_depth = None

        limits = mem["internal_analytics"].get("sla_limits") or DIFFICULTY_LIMITS["medium"]
        max_seconds = limits["max_seconds"]
        elapsed = (datetime.datetime.utcnow() - mem["started_at"]).total_seconds()
        modifier_time = max(0.4, 1.0 - (elapsed - max_seconds) / max_seconds) if elapsed > max_seconds else 1.0

        human_iterations = len([l for l in logs if l["author_type"] == "human"])
        max_depth = limits["max_depth"]
        nest_factor = limits["nest_factor"]
        modifier_depth = min(1.0, human_iterations / (max_depth * nest_factor))
        if human_iterations == 0:
            modifier_depth = 1.0

        if has_logs:
            base_score = (performance_score * 0.50) + (avg_craft * 0.25) + (avg_depth * 0.25)
        else:
            base_score = performance_score
        final_score = round(base_score * modifier_time * modifier_depth, 2)

        mem["status"] = "completed" if is_correct else "failed"
        mem["finished_at"] = datetime.datetime.utcnow()
        mem["final_score"] = final_score
        mem["internal_analytics"]["final_metrics"] = {
            "performance": performance_score,
            "avg_prompt_craft": avg_craft,
            "avg_process_depth": avg_depth,
            "modifier_time": round(modifier_time, 3),
            "modifier_depth": round(modifier_depth, 3),
            "human_iterations": human_iterations,
            "elapsed_seconds": round(elapsed, 1),
        }

        return {
            "status": mem["status"],
            "final_score": final_score,
            "public_feedback": f"Результат решения задачи: {'Успешно' if is_correct else 'Неуспешно'}. Итоговый балл: {final_score} из 100.",
            "analytics_available": True,
        }

    # БД-путь
    result = await db.execute(select(models.TestSession).where(models.TestSession.id == payload.session_id))
    session = result.scalar_one_or_none()
    if not session or session.status != "active":
        raise HTTPException(status_code=400, detail="Session not found or already closed")

    task_data = session.internal_analytics.get("current_task", {})

    # 1. Правильность решения (50%)
    is_correct = task_data.get("correct_answer") == payload.selected_answer
    performance_score = 100.0 if is_correct else 0.0

    # 2. Средние скрытые оценки Prompt Craft / Process Depth из логов
    log_result = await db.execute(
        select(models.PromptLog.prompt_craft_score, models.PromptLog.process_depth_score)
        .where(models.PromptLog.session_id == payload.session_id)
    )
    logs = log_result.all()
    if logs:
        avg_craft = sum([l[0] for l in logs]) / len(logs) * 100
        avg_depth = sum([l[1] for l in logs]) / len(logs) * 100
    else:
        avg_craft = None
        avg_depth = None

    # 3. Модификатор времени (SLA)
    limits = session.internal_analytics.get("sla_limits") or DIFFICULTY_LIMITS["medium"]
    max_seconds = limits["max_seconds"]
    elapsed = (datetime.datetime.utcnow() - session.started_at).total_seconds()
    modifier_time = max(0.4, 1.0 - (elapsed - max_seconds) / max_seconds) if elapsed > max_seconds else 1.0

    # 4. Модификатор глубины (вложенность)
    human_count_res = await db.execute(
        select(func.count(models.PromptLog.id)).where(
            models.PromptLog.session_id == payload.session_id,
            models.PromptLog.author_type == "human",
        )
    )
    human_iterations = int(human_count_res.scalar_one())
    max_depth = limits["max_depth"]
    nest_factor = limits["nest_factor"]
    modifier_depth = min(1.0, human_iterations / (max_depth * nest_factor))
    if human_iterations == 0:
        modifier_depth = 1.0  # нет промптов → глубину не оцениваем и не штрафуем

    # 5. Финальный балл
    if logs:
        base_score = (performance_score * 0.50) + (avg_craft * 0.25) + (avg_depth * 0.25)
    else:
        # Без промптов считается только правильность решения (100%)
        base_score = performance_score
    final_score = round(base_score * modifier_time * modifier_depth, 2)

    # 6. Финализация
    session.status = "completed" if is_correct else "failed"
    session.finished_at = datetime.datetime.utcnow()
    session.task_performance_score = performance_score
    session.prompt_craft_score = avg_craft if avg_craft is not None else 0.0
    session.critical_analysis_score = avg_depth if avg_depth is not None else 0.0
    session.final_score = final_score
    session.public_feedback = (
        f"Результат решения задачи: {'Успешно' if is_correct else 'Неуспешно'}. "
        f"Итоговый балл: {final_score} из 100."
        # ВАЖНО: метрики Prompt Craft / Process Depth в публичном фидбеке не раскрываются
    )
    session.internal_analytics["final_metrics"] = {
        "performance": performance_score,
        "avg_prompt_craft": avg_craft,
        "avg_process_depth": avg_depth,
        "modifier_time": round(modifier_time, 3),
        "modifier_depth": round(modifier_depth, 3),
        "human_iterations": human_iterations,
        "elapsed_seconds": round(elapsed, 1),
    }

    db.add(session)
    await db.commit()

    return {
        "status": session.status,
        "final_score": final_score,
        "public_feedback": session.public_feedback,
        "analytics_available": True,  # HR endpoint можно добавить
    }


@app.get("/session/{session_id}/analytics")
async def session_analytics(session_id: int, db: AsyncSession = Depends(get_db)):
    """Внутренняя аналитика для HR (скрытые метрики)."""
    result = await db.execute(select(models.TestSession).where(models.TestSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.id,
        "status": session.status,
        "final_score": session.final_score,
        "task_performance": session.task_performance_score,
        "prompt_craft": session.prompt_craft_score,
        "critical_analysis": session.critical_analysis_score,
        "internal_analytics": session.internal_analytics,
    }


# ─── Чат с моделью (локальная Ollama / OpenAI) ───

@app.get("/api/chat/status", response_model=schemas.ChatStatusResponse)
async def chat_status():
    """Проверка доступности ИИ-модели для чата."""
    return ai_service.chat_status()


@app.post("/api/chat/send", response_model=Dict[str, Any])
async def chat_send(payload: schemas.ChatRequest):
    """Отправка сообщения в чат с моделью (Ollama локально или OpenAI)."""
    reply = await ai_service.chat_reply(payload.message, context=payload.context)
    return {"reply": reply, "session_id": payload.session_id}


# ─══ Сбор профиля кандидата по email (GitHub API) ══

@app.post("/api/profile/load", response_model=Dict[str, Any])
async def profile_load(payload: schemas.ProfileLoadRequest):
    """Сбор навыков кандидата по email и GitHub-контрибуциям.

    1. Ищет GitHub-пользователя по email (Search API author-email) или логину.
    2. Загружает публичный профиль (имя, био, компания, локация, подписчики).
    3. Сканирует публичные репозитории: языки + темы + звёзды/форки.
    4. Анализирует публичные события (контрибуции): коммиты, PR, issues, ревью.
    5. Если GitHub недоступен — эвристика по локальной части email.
    """
    profile = await profile_service.build_profile_from_email(
        payload.email or "",
        github_username=payload.github_username,
        leetcode_username=payload.leetcode_username,
        linkedin_url=payload.linkedin_url,
        stackoverflow_user_id=payload.stackoverflow_user_id,
        force_refresh=payload.force_refresh,
    )
    return profile
