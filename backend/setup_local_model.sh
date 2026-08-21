#!/usr/bin/env bash
# ============================================================
# No-Resume Skill Market — локальная LLM для чата
# ------------------------------------------------------------
# Устанавливает Ollama и скачивает локальную модель, чтобы
# чат с ИИ-ассистентом работал полностью офлайн (без OpenAI).
#
# После запуска:
#   1. Ollama слушает http://localhost:11434
#   2. Модель доступна в бэкенде по env OLLAMA_MODEL
#   3. /api/chat/status вернёт {"available": true, "provider": "ollama"}
# ============================================================
set -euo pipefail

echo "=========================================="
echo " No-Resume — локальная модель (Ollama)"
echo "=========================================="

# ─── 1. Проверка ОС и установка Ollama ───
if command -v ollama >/dev/null 2>&1; then
  echo "✅ Ollama уже установлен: $(ollama --version)"
else
  echo "📦 Устанавливаю Ollama..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ollama
  elif [[ -f /etc/debian_version ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
  elif [[ -f /etc/redhat-release ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
  else
    echo "⚠️  Не удалось определить ОС. Установите Ollama вручную: https://ollama.com/download"
    exit 1
  fi
fi

# ─── 2. Запуск сервера Ollama (если ещё не запущен) ───
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "✅ Ollama сервер уже запущен"
else
  echo "🚀 Запускаю Ollama сервер..."
  (ollama serve >/dev/null 2>&1 &)
  # Ждём, пока сервер поднимется
  for i in $(seq 1 15); do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
      echo "✅ Ollama сервер запущен"
      break
    fi
    sleep 1
  done
  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "❌ Не удалось запустить Ollama сервер. Запустите вручную: ollama serve"
    exit 1
  fi
fi

# ─── 3. Выбор и загрузка модели ───
# Лёгкая модель для быстрой генерации задач (Qwen 2.5 1.5B ~1.4 ГБ).
# Тяжёлая llama3.1 (4.7 ГБ) генерирует слишком медленно на CPU.
MODEL="${OLLAMA_MODEL:-qwen2.5:1.5b}"
echo "📥 Загружаю модель: $MODEL (это может занять несколько минут)..."
ollama pull "$MODEL"

# ─── 4. Проверка ───
echo ""
echo "=========================================="
echo " ✅ Готово! Локальная модель доступна."
echo "=========================================="
echo "  URL:        http://localhost:11434"
echo "  Модель:     $MODEL"
echo "  Env vars:   OLLAMA_MODEL=$MODEL"
echo "  Env vars:   OLLAMA_BASE_URL=http://localhost:11434"
echo ""
echo "  Перезапустите бэкенд, и /api/chat/status"
echo "  вернёт {\"available\": true, \"provider\": \"ollama\"}"
echo "=========================================="
