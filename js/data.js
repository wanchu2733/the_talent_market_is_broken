// ============================================================
// No-Resume Skill Market — дынный слой платформы (Mock Data)
// ============================================================

window.PLATFORM_DATA = {
  // Актуальный словарь технологий (динамический чек-лист)
  skills: [
    // Backend
    { id: 'python', name: 'Python', category: 'Backend', level: 'core' },
    { id: 'fastapi', name: 'FastAPI', category: 'Backend', level: 'framework' },
    { id: 'django', name: 'Django', category: 'Backend', level: 'framework' },
    { id: 'nodejs', name: 'Node.js', category: 'Backend', level: 'core' },
    { id: 'go', name: 'Go', category: 'Backend', level: 'core' },
    { id: 'rust', name: 'Rust', category: 'Backend', level: 'core' },
    { id: 'sql', name: 'SQL', category: 'Backend', level: 'core' },
    { id: 'postgresql', name: 'PostgreSQL', category: 'Backend', level: 'db' },
    { id: 'mongodb', name: 'MongoDB', category: 'Backend', level: 'db' },
    { id: 'redis', name: 'Redis', category: 'Backend', level: 'db' },
    { id: 'microservices', name: 'Microservices', category: 'Backend', level: 'architecture' },
    { id: 'rabbitmq', name: 'RabbitMQ / Kafka', category: 'Backend', level: 'infra' },
    { id: 'docker', name: 'Docker', category: 'DevOps', level: 'infra' },
    { id: 'kubernetes', name: 'Kubernetes', category: 'DevOps', level: 'infra' },
    { id: 'cicd', name: 'CI/CD (GitHub Actions)', category: 'DevOps', level: 'infra' },
    { id: 'aws', name: 'AWS', category: 'DevOps', level: 'cloud' },
    { id: 'gcp', name: 'GCP', category: 'DevOps', level: 'cloud' },

    // Frontend
    { id: 'javascript', name: 'JavaScript (ES2024)', category: 'Frontend', level: 'core' },
    { id: 'typescript', name: 'TypeScript', category: 'Frontend', level: 'core' },
    { id: 'react', name: 'React', category: 'Frontend', level: 'framework' },
    { id: 'nextjs', name: 'Next.js', category: 'Frontend', level: 'framework' },
    { id: 'vue', name: 'Vue / Nuxt', category: 'Frontend', level: 'framework' },
    { id: 'css', name: 'CSS / Tailwind', category: 'Frontend', level: 'styling' },
    { id: 'webpack', name: 'Webpack / Vite', category: 'Frontend', level: 'tooling' },

    // AI / Data
    { id: 'llm', name: 'LLM / Prompt Engineering', category: 'AI & Data', level: 'ai' },
    { id: 'openai', name: 'OpenAI API / GPT', category: 'AI & Data', level: 'ai' },
    { id: 'langchain', name: 'LangChain / Agents', category: 'AI & Data', level: 'ai' },
    { id: 'rag', name: 'RAG Pipeline', category: 'AI & Data', level: 'ai' },
    { id: 'ml', name: 'ML / scikit-learn', category: 'AI & Data', level: 'ai' },
    { id: 'pytorch', name: 'PyTorch', category: 'AI & Data', level: 'ai' },
    { id: 'pandas', name: 'Pandas / NumPy', category: 'AI & Data', level: 'data' },
    { id: 'spark', name: 'Apache Spark', category: 'AI & Data', level: 'data' },

    // Design
    { id: 'figma', name: 'Figma', category: 'Design', level: 'design' },
    { id: 'uiux', name: 'UI/UX Audit', category: 'Design', level: 'design' },
    { id: 'designsystems', name: 'Design Systems', category: 'Design', level: 'design' },

    // Soft & architecture
    { id: 'systemdesign', name: 'System Design', category: 'Soft & Architecture', level: 'architecture' },
    { id: 'algorithms', name: 'Алгоритмы / LeetCode', category: 'Soft & Architecture', level: 'core' },
    { id: 'tdd', name: 'TDD / Unit Tests', category: 'Soft & Architecture', level: 'practice' },
    { id: 'agile', name: 'Agile / Scrum', category: 'Soft & Architecture', level: 'practice' },
    { id: 'promptcritique', name: 'Критика ИИ (галлюцинации)', category: 'Soft & Architecture', level: 'ai' },
  ],

  // Категории для фильтра
  skillCategories: ["Backend", "Frontend", "DevOps", "AI & Data", "Design", "Soft & Architecture"],

  // Компании-работодатели с весами требований
  companies: [
    {
      id: 'c1',
      name: 'TechNova GmbH',
      industry: 'FinTech',
      logo: 'TN',
      color: '#6c5ce7',
      position: 'Backend Engineer / FastAPI',
      vacancyStatus: 'confirmed', // confirmed | pending_expire | archived
      lastVerifiedDays: 5,
      weights: {
        python: 90,
        fastapi: 95,
        sql: 75,
        postgresql: 80,
        llm: 85,
        docker: 70,
        microservices: 60,
        systemdesign: 50,
        algorithms: 65,
        promptcritique: 80
      },
      threshold: 75, // Порог совпадения для этого оффера
      bar: [
        { skill: 'Python / FastAPI', weight: 92 },
        { skill: 'LLM + Prompting', weight: 85 },
        { skill: 'PostgreSQL', weight: 78 },
        { skill: 'System Design', weight: 55 }
      ]
    },
    {
      id: 'c2',
      name: 'NovaBank',
      industry: 'Banking / Cybersecurity',
      logo: 'NB',
      color: '#0984e3',
      position: 'Senior Go Engineer',
      vacancyStatus: 'confirmed',
      lastVerifiedDays: 2,
      weights: {
        go: 95,
        microservices: 85,
        algorithms: 80,
        postgresql: 70,
        docker: 75,
        kubernetes: 65,
        systemdesign: 90,
        redis: 60,
        cicd: 70,
        promptcritique: 60
      },
      threshold: 75,
      bar: [
        { min: 'Go / Rust', weight: 90 },
        { min: 'System Design', weight: 85 },
        { min: 'Алгоритмы', weight: 80 },
        { min: 'Kubernetes', weight: 65 }
      ]
    },
    {
      id: 'c3',
      name: 'DesignHub',
      industry: 'Creative / AI-арт',
      logo: 'DH',
      color: '#fd79a8',
      position: 'UX/UI + AI Artist',
      vacancyStatus: 'confirmed',
      lastVerifiedDays: 7,
      weights: {
        figma: 90,
        uiux: 95,
        designsystems: 70,
        llm: 80,
        openai: 75,
        promptcritique: 70,
        rag: 40,
        javascript: 60,
        css: 75
      },
      threshold: 70,
      bar: [
        { min: 'Figma', weight: 90 },
        { min: 'UI/UX Audit', weight: 92 },
        { min: 'LLM / AI-арт', weight: 78 },
        { min: 'CSS', weight: 60 }
      ]
    },
    {
      id: 'c4',
      name: 'DataSprint',
      industry: 'Analytics / ML',
      logo: 'DS',
      color: '#00b894',
      position: 'ML Engineer (LLM/RAG)',
      vacancyStatus: 'confirmed',
      lastVerifiedDays: 1,
      weights: {
        python: 95,
        llm: 95,
        rag: 90,
        langchain: 85,
        openai: 80,
        pytorch: 75,
        pandas: 80,
        ml: 70,
        sql: 75,
        promptcritique: 90
      },
      threshold: 72,
      bar: [
        { skill: 'Python', weight: 95 },
        { skill: 'LLM/RAG', weight: 95 },
        { skill: 'LangChain', weight: 85 },
        { skill: 'SQL', weight: 75 }
      ]
    },
    {
      id: 'c5',
      name: 'CloudStack',
      industry: 'Cloud Infrastructure',
      logo: 'CS',
      color: '#e17055',
      position: 'DevOps / SRE',
      vacancyStatus: 'pending_expire', // Вакансия на грани скрытия (7 дней не подтверждена)
      lastVerifiedDays: 9,
      weights: {
        docker: 95,
        kubernetes: 90,
        aws: 85,
        cicd: 90,
        sql: 60,
        python: 80,
        microservices: 70,
        redis: 65,
        systemdesign: 60,
        promptcritique: 60
      },
      threshold: 70,
      bar: [
        { skill: 'Docker', weight: 90 },
        { skill: 'K8s / Helm', weight: 85 },
        { skill: 'AWS', weight: 85 },
        { skill: 'CI/CD', weight: 82 }
      ]
    },
  ],

  // Сценарии тестов (геймификация)
  scenarios: {
    text: {
      title: "Текстовый сценарий",
      description: "Симуляция общения с капризным клиентом и декомпозиция бизнес-задачи",
      icon: "💬",
      default: {
        task: "Клиент принес очень короткое ТЗ: «Сделайте нам система». Он не знает, что хочет, но уверен, что ему нужно «блокчейн, ИИ и чтобы красиво». Ваша задача — в течение 5 минут взаимодействия с ИИ-клиентом: 1) Выяснить настоящую задачу, 2) Задать правильные вопросы вместо того чтобы сразу соглашаться, 3) Разложить задачу на этапы с оценкой рисков.",
        metrics: [
          'Глубина понимания ТЗ',
          'Уточняющие вопросы',
          'Декомпозиция',
          'Структура ответа'
        ]
      }
    },
    coding: {
      title: "Coding Live-экран",
      description: "Написание микросервиса с ИИ-копилотом и защита от галлюцинаций",
      icon: "⌨️",
      default: {
        task: `Реализуй микросервис для внутренней системы компании. Стек: FastAPI + PostgreSQL.
Требования:
1) GET /api/users — вернуть список пользователей с пагинацией
2) POST /api/users — создать пользователя (email уникален, пароль в формате bcrypt-FAKE запрещен по security policy)
3) Обработка ошибок: 404, 422, 500

Кодовый старт (уже есть частично, но в нем есть баг ТЗ):`,
        starterCode: `from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List

app = FastAPI()

users_db = []  # in-memory

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

@app.get("/api/users")
def get_users(page: int = 1, limit: int = 10):
    # Баг: нет проверки пагинации
    start = (page - 1) * limit
    return users_db[start:start + limit]

@app.post("/api/users", status_code=201)
def create_user(data: UserCreate):
    # TODO: добавить валидацию уникальности email
    return data
`,
        metrics: [
          'Точность промптов',
          'Найдены баги ТЗ',
          'Скорость итераций',
          'Архитектура решения'
        ]
      }
    },
    visual: {
      title: "Visual-контент",
      description: "Поиск бага на дизайн-макете и UI/UX аудит интерфейса",
      icon: "🎨",
      default: {
        task: "Перед вами макет страницы облacти личного кабинета. Найди 4 скрытых бага (несоответствие контрасту, отсутсвие состояний, сломанный flow заказа, недостпнотсь элемента) и опиши исправления.",
        actions: [
          { 'id': 'bug1', label: 'Кнопка «Заказать» не имеет hover/disabled состояний', found: false },
          { 'id': 'bug2', label: 'Контраст текста 2.4:1 (не походит WCAG AA)', found: false },
          { 'id': 'bug3', label: 'Отсутствует подтверждение после отправки формы', found: false },
          { 'id': 'bug4', label: 'Пагинация не скроллит к списку (ломаный flow)', found: false }
        ],
        metrics: [
          'Внимательность к деталям',
          'UI/UX аудит',
          'Системное мышление'
        ]
      }
    }
  },

  // Вопросы для "текстового" этапа (оценка промптинга)
  promptQuestions: [
    {
      id: 'q1',
      type: 'choice',
      question: 'Клиент говорит: «Нужно как можно быстрее, это срочно!». Ваше действие как «архитектора процесса»?',
      options: [
        { text: 'Сразу начать предлагать конкретное решение (стек, сроки)', score: 30, feedback: 'Слишком рано. Без понимания бизнес-цели решение совдания ' },
        { text: 'Задать ключевые уточняющие вопросы: для кого, какая польза, метрики успеха, ограничения', score: 95, feedback: 'Отлично — вы архитекруетепроенс, уточняете цел ' },
        { text: 'Сказать «Ок» и попросит дов ТЗ письменно, чтобы ничего не обещать ', score: 60, feedback: 'Частично верно — нужен баланс между сбором ТЗ и живым уточнением' }
      ]
    },
    {
      id: 'q2',
      type: 'prompt',
      question: 'Напишите промпт для ИИ-помощника, чтобы он разложил задачу клиента на MVP и отбросил лишнее «блокчейн и нейросети».',
      placeholder: 'Например: «Ты — старший продакт-менеджер...»',
      rubric: ['Роль (персона) для ИИ', 'Контекст задачи', 'Конкретные выходные (список этапов)', 'Критерии отбрасывания лишнего'],
      maxScore: 100
    },
    {
      id: 'q3',
      type: 'tricky',
      question: 'ИИ-ассистент в начале работы выдал галлюцинацию: «для этого проекта рекомендуем стек из 14 блокчейнов и Web3 DAO». Выберите критически верный ответ:',
      options: [
        { text: 'Согласиться — ИИ знает лучше', score: 5 },
        { text: 'Промптить ИИ с факт-чекингом: проверить соответствие реальной задаче клиента', score: 95 },
        { text: 'Сменить запрос к другой модели', score: 45 }
      ]
    },
    {
      id: 'q4',
      type: 'choice',
      question: 'Кандидат на вашем тесте набраб 65% (порог был 80%). Что должна сделать система?',
      options: [
        { text: 'Отказ без объяснения', score: 0 },
        { text: 'Сформировть ИИ-карту развития о фчеркаб, и предложить компанию с порогом <=65% (карусель офферов)', score: 100 },
        { text: 'Дать шанс перепроuble без лимита', score: 40 }
      ]
    }
  ],

  // Обучающие материалы для карты развития
  learningResources: [
    { skill: 'LLM / prompt', title: 'Prompt Engineering Guide', url: 'https://www.promptingguide.ai', type: 'article' },
    { skill: 'LLM / prompt', title: "OpenAI Cookbook", url: 'https://cookbook.openai.com', type: 'courses' },
    { skill: 'python', title: 'FastAPI official docs', url: 'https://fastapi.tiangolo.com', type: 'docs' },
    { skill: 'algorithms', title: 'NeetCode Roadmap', url: 'https://neetcode.io', type: 'practice' },
    { skill: 'systemdesign', title: 'System Design Primer (GitHub)', url: 'https://github.com/donnemartin/system-design-primer', type: 'repo' },
    { skill: 'docker', title: 'Docker curriculum by Ben Gryn', url: 'https://docs.docker.com/get-started', type: 'docs' },
    { skill: 'llm', title: 'Hugging Face Course', url: 'https://huggingface.co/learn', type: 'courses' },
    { skill: 'sql', title: 'PG Exercises', url: 'https://pgexercises.com', type: 'practice' },
    { skill: 'rag', title: 'RAG from scratch — DeepLearning.AI', url: 'https://www.deeplearning.ai/short-courses/', type: 'courses' },
    { skill: 'uiux', title: 'Laws of UX', url: 'https://lawsofux.com', type: 'article' },
  ],

  // Карусель офферов — компании готовые нанять с данным баллом
  // Второй рынок
  altOffers: [
    { companyId: 'c5', matchScore: 68, note: 'DevOps, порог 70% — почти у цели' },
    { companyId: 'c3', matchScore: 65, note: 'UX/UI+AI, порог 70%' },
  ],
};