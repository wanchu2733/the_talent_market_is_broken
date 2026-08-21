"""Сервис сбора профиля кандидата по email и GitHub-контрибуциям.

Источники данных:
1. Поиск GitHub-пользователя по email через Search API (author-email).
2. Профиль пользователя (имя, био, компания, локация, подписчики и т.д.).
3. Публичные репозитории: языки, темы, звёзды, форки.
4. Публичные события (events): коммиты, pull request'ы, issues —
   анализ реальной активности/контрибуций.

Если GitHub недоступен или email не найден — возвращаем эвристический мок
по локальной части email (чтобы UI всегда работал).
"""
import datetime
import os
import re
import time
from typing import Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

# ─── In-memory кэш (динамическое обновление профиля) ───
_PROFILE_CACHE: Dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 час

# ─── Маппинг языков GitHub → навыки платформы ───
LANGUAGE_TO_SKILL: Dict[str, List[str]] = {
    "python": ["python"],
    "go": ["go"],
    "rust": ["rust"],
    "javascript": ["javascript", "nodejs"],
    "typescript": ["typescript", "javascript"],
    "css": ["css"],
    "html": ["css"],
    "scss": ["css"],
    "sass": ["css"],
    "dockerfile": ["docker"],
    "shell": ["cicd"],
    "makefile": ["cicd"],
    "cmake": ["cicd"],
    "yaml": ["kubernetes"],
    "hcl": ["aws"],
    "terraform": ["aws"],
    "sql": ["sql"],
    "plpgsql": ["postgresql", "sql"],
    "jupyter notebook": ["ml", "pandas"],
    "jupyter": ["ml", "pandas"],
    "java": ["spark"],
    "scala": ["spark"],
    "r": ["pandas", "ml"],
}

# ─── Маппинг тем (topics) GitHub → навыки платформы ───
TOPIC_TO_SKILL: Dict[str, List[str]] = {
    "fastapi": ["fastapi", "python"],
    "django": ["django", "python"],
    "flask": ["python"],
    "react": ["react", "javascript"],
    "reactjs": ["react", "javascript"],
    "nextjs": ["nextjs", "typescript"],
    "vue": ["vue", "javascript"],
    "vuejs": ["vue", "javascript"],
    "nuxt": ["vue"],
    "nuxtjs": ["vue"],
    "tailwind": ["css"],
    "tailwindcss": ["css"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes"],
    "k8s": ["kubernetes"],
    "aws": ["aws"],
    "gcp": ["gcp"],
    "google-cloud": ["gcp"],
    "azure": ["aws"],
    "terraform": ["aws"],
    "machine-learning": ["ml", "llm"],
    "deep-learning": ["ml", "pytorch"],
    "pytorch": ["pytorch", "ml"],
    "tensorflow": ["ml"],
    "langchain": ["langchain", "llm"],
    "llamaindex": ["rag", "llm"],
    "rag": ["rag", "llm"],
    "llm": ["llm"],
    "openai": ["openai", "llm"],
    "gpt": ["openai", "llm"],
    "chatgpt": ["openai", "llm"],
    "prompt-engineering": ["llm", "promptcritique"],
    "figma": ["figma"],
    "ui-ux": ["uiux", "figma"],
    "uiux": ["uiux"],
    "design-system": ["designsystems"],
    "design-systems": ["designsystems"],
    "system-design": ["systemdesign"],
    "microservices": ["microservices"],
    "postgresql": ["postgresql", "sql"],
    "postgres": ["postgresql", "sql"],
    "mongodb": ["mongodb"],
    "mongo": ["mongodb"],
    "redis": ["redis"],
    "rabbitmq": ["rabbitmq"],
    "kafka": ["rabbitmq"],
    "algorithms": ["algorithms"],
    "leetcode": ["algorithms"],
    "tdd": ["tdd"],
    "agile": ["agile"],
    "scrum": ["agile"],
    "devops": ["docker", "cicd"],
    "sre": ["docker", "kubernetes"],
    "data-science": ["pandas", "ml"],
    "data-engineering": ["spark", "sql"],
    "apache-spark": ["spark"],
    "pandas": ["pandas"],
    "numpy": ["pandas"],
    "scikit-learn": ["ml"],
    "graphql": ["fastapi"],
    "grpc": ["microservices"],
    "web3": ["llm"],
    "blockchain": ["llm"],
}


def _gh_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NoResumeProfileBot/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _map_language(lang: str) -> List[str]:
    return LANGUAGE_TO_SKILL.get(lang.lower(), [])


def _map_topic(topic: str) -> List[str]:
    return TOPIC_TO_SKILL.get(topic.lower(), [])


async def _github_get(url: str, params: Optional[dict] = None) -> Optional[dict]:
    """Безопасный GET-запрос к GitHub API. Возвращает JSON или None."""
    if httpx is None:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=_gh_headers())
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def _github_search_user_by_email(email: str) -> Optional[str]:
    """Ищет GitHub-логин по email через Search API (author-email)."""
    data = await _github_get(
        "https://api.github.com/search/commits",
        params={"q": f"author-email:{email}", "per_page": 1},
    )
    if not data:
        return None
    items = data.get("items", [])
    if items:
        return items[0].get("author", {}).get("login")
    return None


async def _github_user_profile(username: str) -> Optional[dict]:
    """Получает публичный профиль пользователя GitHub."""
    return await _github_get(f"https://api.github.com/users/{username}")


async def _github_user_repos(username: str) -> List[dict]:
    """Получает собственные (НЕ форкнутые) публичные репозитории пользователя.

    Форки исключаются: они не отражают реальный вклад кандидата.
    """
    data = await _github_get(
        f"https://api.github.com/users/{username}/repos",
        params={"per_page": 100, "sort": "updated"},
    )
    if not isinstance(data, list):
        return []
    return [r for r in data if not r.get("fork", False)]


async def _github_repo_languages(owner: str, repo: str) -> Dict[str, int]:
    """Получает языки репозитория."""
    data = await _github_get(
        f"https://api.github.com/repos/{owner}/{repo}/languages"
    )
    return data if isinstance(data, dict) else {}


async def _github_repo_topics(owner: str, repo: str) -> List[str]:
    """Получает темы (topics) репозитория."""
    data = await _github_get(
        f"https://api.github.com/repos/{owner}/{repo}/topics",
        params={"per_page": 20},
    )
    if isinstance(data, dict):
        return data.get("names", [])
    return []


async def _github_user_events(username: str) -> List[dict]:
    """Получает публичные события (контрибуции) пользователя — до 100."""
    data = await _github_get(
        f"https://api.github.com/users/{username}/events/public",
        params={"per_page": 100},
    )
    return data if isinstance(data, list) else []


async def _github_commits_search(query: str) -> dict:
    """Поиск коммитов через GitHub Search API (требует cloak-preview заголовок).

    Возвращает полный JSON с items (коммиты по всему GitHub, включая чужие репозитории).
    """
    if httpx is None:
        return {}
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "User-Agent": "NoResumeProfileBot/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.github.com/search/commits",
                params={"q": query, "per_page": 100},
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {}


def _repo_owner_from_full_name(repo_full: str) -> str:
    """Извлекает владельца из 'owner/repo'."""
    if not repo_full or "/" not in repo_full:
        return ""
    return repo_full.split("/")[0]


def _repo_owner_from_url(repo_url: str) -> str:
    """Извлекает 'owner/repo' из repository_url (issues/PR)."""
    if not repo_url:
        return ""
    marker = "https://api.github.com/repos/"
    if marker in repo_url:
        return repo_url.split(marker)[-1]
    return ""


async def _github_search_external_contributions(username: str) -> Dict[str, object]:
    """Ищет контрибуции пользователя в ЧУЖИХ проектах (не в своих репозиториях).

    Источники:
    - Search commits по author (коммиты по всему GitHub)
    - Search issues по author type:pr (pull request'ы в чужие репозитории)
    - Search issues по author type:issue (открытые issues)
    """
    external_repos = set()
    external_orgs = set()
    external_commits = 0
    external_prs = 0
    external_issues = 0

    # 1. Коммиты (автор) — по всему GitHub
    commits_data = await _github_commits_search(f"author:{username}")
    for item in commits_data.get("items", []):
        repo_full = item.get("repository", {}).get("full_name", "")
        owner = _repo_owner_from_full_name(repo_full)
        if owner and owner.lower() != username.lower():
            external_commits += 1
            external_repos.add(repo_full)
            external_orgs.add(owner)

    # 2. Pull request'ы (автор) в чужие репозитории
    prs_data = await _github_get(
        "https://api.github.com/search/issues",
        params={"q": f"author:{username} type:pr", "per_page": 100},
    )
    if prs_data and isinstance(prs_data, dict):
        for item in prs_data.get("items", []):
            repo_full = _repo_owner_from_url(item.get("repository_url", ""))
            owner = _repo_owner_from_full_name(repo_full)
            if owner and owner.lower() != username.lower():
                external_prs += 1
                external_repos.add(repo_full)
                external_orgs.add(owner)

    # 3. Issues (автор) в чужие репозитории
    issues_data = await _github_get(
        "https://api.github.com/search/issues",
        params={"q": f"author:{username} type:issue", "per_page": 100},
    )
    if issues_data and isinstance(issues_data, dict):
        for item in issues_data.get("items", []):
            repo_full = _repo_owner_from_url(item.get("repository_url", ""))
            owner = _repo_owner_from_full_name(repo_full)
            if owner and owner.lower() != username.lower():
                external_issues += 1
                external_repos.add(repo_full)
                external_orgs.add(owner)

    return {
        "external_commits": external_commits,
        "external_prs": external_prs,
        "external_issues": external_issues,
        "external_repos_count": len(external_repos),
        "external_repos": sorted(external_repos)[:20],
        "external_orgs_count": len(external_orgs),
        "external_orgs": sorted(external_orgs)[:20],
    }


async def _proxycurl_profile(linkedin_url: str) -> Optional[dict]:
    """Собирает структурированные данные LinkedIn/XING через Proxycurl API.

    Proxycurl — лучший источник для Европы (XING + LinkedIn) с JSON-выводом.
    """
    if httpx is None:
        return None
    api_key = os.getenv("PROXYCURL_API_KEY")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://nubela.co/proxycurl/api/v2/linkedin",
                params={"linkedin_profile_url": linkedin_url, "use_cache": "if-present"},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "full_name": data.get("full_name"),
                    "headline": data.get("headline"),
                    "summary": data.get("summary"),
                    "industry": data.get("industry"),
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "experience_count": len(data.get("experiences", [])),
                    "education_count": len(data.get("education", [])),
                    "skills": data.get("skills") or [],
                    "followers": data.get("follower_count"),
                    "connections": data.get("connections_count"),
                    "languages": data.get("languages") or [],
                }
    except Exception:
        pass
    return None


async def _proxycurl_search_xing(keyword: str) -> Optional[dict]:
    """Поиск профилей XING по ключевому слову через Proxycurl (Search API)."""
    if httpx is None:
        return None
    api_key = os.getenv("PROXYCURL_API_KEY")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://nubela.co/proxycurl/api/search/company",
                params={"keyword": keyword, "country": "DE"},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "companies_found": len(data.get("results", [])),
                    "companies": [c.get("name") for c in data.get("results", [])[:10]],
                }
    except Exception:
        pass
    return None


async def _stackoverflow_profile(user_id: int) -> Optional[dict]:
    """Собирает данные Stack Overflow через Stack Exchange API."""
    if httpx is None:
        return None
    key = os.getenv("STACKEXCHANGE_KEY", "")
    params = {"site": "stackoverflow", "key": key} if key else {"site": "stackoverflow"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Профиль
            resp = await client.get(
                f"https://api.stackexchange.com/2.3/users/{user_id}",
                params=params,
                headers={"User-Agent": "NoResumeProfileBot/1.0"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return None
            user = items[0]
            # Top-теги
            tags_resp = await client.get(
                f"https://api.stackexchange.com/2.3/users/{user_id}/top-tags",
                params=params,
                headers={"User-Agent": "NoResumeProfileBot/1.0"},
            )
            top_tags = []
            if tags_resp.status_code == 200:
                tags_data = tags_resp.json()
                top_tags = [
                    {"tag": t.get("tag_name"), "score": t.get("answer_score")}
                    for t in tags_data.get("items", [])[:10]
                ]
            return {
                "display_name": user.get("display_name"),
                "reputation": user.get("reputation"),
                "accept_rate": user.get("accept_rate"),
                "gold_badges": (user.get("badge_counts") or {}).get("gold", 0),
                "silver_badges": (user.get("badge_counts") or {}).get("silver", 0),
                "bronze_badges": (user.get("badge_counts") or {}).get("bronze", 0),
                "top_tags": top_tags,
            }
    except Exception:
        pass
    return None


async def _hunter_email_verification(email: str) -> Optional[dict]:
    """Верифицирует корпоративный email через Hunter.io API."""
    if httpx is None:
        return None
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": api_key},
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "status": data.get("status"),
                    "result": data.get("result"),
                    "score": data.get("score"),
                    "regexp": data.get("regexp"),
                    "gibberish": data.get("gibberish"),
                    "disposable": data.get("disposable"),
                    "webmail": data.get("webmail"),
                }
    except Exception:
        pass
    return None


async def _leetcode_profile(username: str) -> Optional[dict]:
    """Собирает данные с LeetCode через GraphQL API.

    Возвращает: решённые задачи (всего + по сложности), рейтинг, репутацию,
    очки контрибуций.
    """
    if httpx is None:
        return None
    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        username
        submitStats {
          acSubmissionNum { difficulty count }
        }
        profile { ranking reputation }
        contributions { points }
      }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {"username": username}},
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "NoResumeProfileBot/1.0",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                matched = data.get("data", {}).get("matchedUser")
                if matched:
                    stats = matched.get("submitStats", {}).get("acSubmissionNum", [])
                    total_solved = 0
                    by_difficulty: Dict[str, int] = {}
                    for s in stats:
                        diff = s.get("difficulty", "unknown")
                        cnt = s.get("count", 0)
                        by_difficulty[diff] = cnt
                        total_solved += cnt
                    profile = matched.get("profile", {}) or {}
                    contributions = matched.get("contributions", {}) or {}
                    return {
                        "username": matched.get("username"),
                        "total_solved": total_solved,
                        "by_difficulty": by_difficulty,
                        "ranking": profile.get("ranking"),
                        "reputation": profile.get("reputation"),
                        "contribution_points": contributions.get("points"),
                    }
    except Exception:
        pass
    return None


def _cache_key(email: str, username: Optional[str]) -> str:
    return f"{email}|{username or ''}"


def _cache_get(key: str) -> Optional[dict]:
    entry = _PROFILE_CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL_SECONDS:
        return entry["data"]
    return None


def _cache_set(key: str, data: dict) -> None:
    _PROFILE_CACHE[key] = {"ts": time.time(), "data": data}


def _analyze_contributions(events: List[dict]) -> Dict[str, object]:
    """Анализирует публичные события и считает метрики контрибуций."""
    stats: Dict[str, int] = {
        "total_commits": 0,
        "pull_requests": 0,
        "issues_opened": 0,
        "issues_closed": 0,
        "reviews": 0,
        "pull_requests_merged": 0,
        "stars_given": 0,
        "forks_created": 0,
    }
    active_days = set()
    last_activity_at: Optional[str] = None

    for ev in events:
        etype = ev.get("type", "")
        created_at = ev.get("created_at")
        if created_at:
            active_days.add(created_at[:10])
            if last_activity_at is None or created_at > last_activity_at:
                last_activity_at = created_at

        payload = ev.get("payload") or {}
        if etype == "PushEvent":
            commits = payload.get("commits") or []
            stats["total_commits"] += len(commits)
        elif etype == "PullRequestEvent":
            stats["pull_requests"] += 1
            action = payload.get("action")
            if action == "closed" and payload.get("pull_request", {}).get("merged") is True:
                stats["pull_requests_merged"] += 1
        elif etype == "IssuesEvent":
            action = payload.get("action")
            if action == "opened":
                stats["issues_opened"] += 1
            elif action == "closed":
                stats["issues_closed"] += 1
        elif etype == "PullRequestReviewEvent":
            stats["reviews"] += 1
        elif etype == "WatchEvent":
            stats["stars_given"] += 1
        elif etype == "ForkEvent":
            stats["forks_created"] += 1

    return {
        "total_commits": stats["total_commits"],
        "pull_requests": stats["pull_requests"],
        "issues_opened": stats["issues_opened"],
        "issues_closed": stats["issues_closed"],
        "reviews": stats["reviews"],
        "pull_requests_merged": stats["pull_requests_merged"],
        "stars_given": stats["stars_given"],
        "forks_created": stats["forks_created"],
        "active_days": len(active_days),
        "events_analyzed": len(events),
        "last_activity_at": last_activity_at,
    }


def _build_top_repos(repos: List[dict], limit: int = 5) -> List[dict]:
    """Формирует топ репозиториев по звёздам."""
    top = sorted(
        repos,
        key=lambda r: (r.get("stargazers_count") or 0) + (r.get("forks_count") or 0) * 2,
        reverse=True,
    )[:limit]
    result = []
    for repo in top:
        result.append({
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count") or 0,
            "forks": repo.get("forks_count") or 0,
            "topics": repo.get("topics") or [],
            "updated_at": repo.get("updated_at"),
            "html_url": repo.get("html_url"),
        })
    return result


def _profile_age_days(created_at: Optional[str]) -> Optional[int]:
    """Возраст GitHub-аккаунта в днях."""
    if not created_at:
        return None
    try:
        created = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        return max(0, (now - created).days)
    except Exception:
        return None


async def build_profile_from_email(
    email: str,
    github_username: Optional[str] = None,
    leetcode_username: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    stackoverflow_user_id: Optional[int] = None,
    force_refresh: bool = False,
) -> dict:
    """Собирает профиль кандидата по email и/или GitHub-логину.

    Источники: GitHub (репозитории/контрибуции/чужие проекты), LeetCode,
    Proxycurl (LinkedIn/XING), Stack Overflow, Hunter.io (верификация email).

    Данные кэшируются на 1 час (CACHE_TTL_SECONDS) для динамического обновления.
    force_refresh=True принудительно пересобирает профиль.

    Возвращает:
        {
            "email": str,
            "github_username": str | None,
            "skills": [str],
            "source": "github" | "local-mock",
            "repos_found": int,
            "profile": {...} | None,
            "contributions": {...} | None,
            "top_repos": [...],
            "linkedin": {...} | None,
            "stackoverflow": {...} | None,
            "email_verification": {...} | None,
            "xing_search": {...} | None,
        }
    """
    skills: List[str] = []
    username: Optional[str] = github_username
    repos_found = 0
    profile: Optional[dict] = None
    contributions: Optional[dict] = None
    top_repos: List[dict] = []
    linkedin_data: Optional[dict] = None
    stackoverflow_data: Optional[dict] = None
    email_verification: Optional[dict] = None
    xing_search: Optional[dict] = None

    # 0. Если email не передан — генерируем псевдо-email
    if not email:
        email = f"{username or 'candidate'}@github.local"

    # 0.1 Проверяем кэш (динамическое обновление)
    cache_key = _cache_key(email, username or leetcode_username)
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached:
            cached["cached"] = True
            cached["cache_age_seconds"] = CACHE_TTL_SECONDS
            return cached

    # 1. Если логин не передан — ищем по email через Search API
    if not username:
        username = await _github_search_user_by_email(email)

    # 2. Сбор данных по найденному логину
    if username:
        # 2.1 Профиль пользователя
        raw_profile = await _github_user_profile(username)
        if raw_profile:
            profile = {
                "name": raw_profile.get("name"),
                "login": raw_profile.get("login"),
                "bio": raw_profile.get("bio"),
                "company": raw_profile.get("company"),
                "location": raw_profile.get("location"),
                "email": raw_profile.get("email"),
                "blog": raw_profile.get("blog"),
                "followers": raw_profile.get("followers") or 0,
                "following": raw_profile.get("following") or 0,
                "public_repos": raw_profile.get("public_repos") or 0,
                "public_gists": raw_profile.get("public_gists") or 0,
                "avatar_url": raw_profile.get("avatar_url"),
                "html_url": raw_profile.get("html_url"),
                "created_at": raw_profile.get("created_at"),
                "account_age_days": _profile_age_days(raw_profile.get("created_at")),
            }

        # 2.2 Репозитории → навыки (языки + темы) + звёзды/форки
        repos = await _github_user_repos(username)
        repos_found = len(repos)

        all_contrib_stars = 0
        all_contrib_forks = 0
        for repo in repos:
            owner = repo.get("owner", {}).get("login", username)
            name = repo.get("name", "")
            if not name:
                continue

            all_contrib_stars += repo.get("stargazers_count") or 0
            all_contrib_forks += repo.get("forks_count") or 0

            # Одноимённый язык из поля repo["language"] — сразу
            lang_field = repo.get("language")
            if lang_field:
                for s in _map_language(str(lang_field)):
                    if s not in skills:
                        skills.append(s)

            # Полный список языков
            langs = await _github_repo_languages(owner, name)
            for lang in langs:
                for s in _map_language(lang):
                    if s not in skills:
                        skills.append(s)

            # Темы
            topics = await _github_repo_topics(owner, name)
            # Сохраняем темы в репозиторий для top_repos
            repo["_topics"] = topics
            for topic in topics:
                for s in _map_topic(topic):
                    if s not in skills:
                        skills.append(s)

        # 2.3 Публичные события → контрибуции
        events = await _github_user_events(username)
        contributions = _analyze_contributions(events)
        contributions = {
            **contributions,
            "stars_received": all_contrib_stars,
            "forks_received": all_contrib_forks,
        }

        # 2.4 Топ репозиториев
        top_repos = _build_top_repos(repos)

        # 2.5 Контрибуции в ЧУЖИХ проектах (GitHub Search API)
        external_contrib = await _github_search_external_contributions(username)
        contributions = {**contributions, **external_contrib}

        # 2.6 LeetCode (отдельный логин или совпадает с GitHub)
        leetcode_user = leetcode_username or username
        leetcode = await _leetcode_profile(leetcode_user)
        if leetcode:
            # LeetCode подтверждает навык algorithms
            if "algorithms" not in skills:
                skills.append("algorithms")
            profile = profile or {}
            profile["leetcode"] = leetcode

    # 2.7 Proxycurl: LinkedIn / XING (DACH-источник №1)
    if linkedin_url:
        linkedin_data = await _proxycurl_profile(linkedin_url)
        if linkedin_data:
            for s in linkedin_data.get("skills", []):
                norm = s.lower()
                mapped = _map_topic(norm) or _map_language(norm)
                if mapped:
                    for skill in mapped:
                        if skill not in skills:
                            skills.append(skill)
                else:
                    # Нормализуем произвольный навык LinkedIn в snake_case id
                    skill_id = re.sub(r"[^a-z0-9]+", "", norm)
                    if skill_id and skill_id not in skills:
                        skills.append(skill_id)

    # 2.8 Верификация email (Hunter.io) — для корпоративных адресов
    if email and "@" in email and not email.endswith("@github.local"):
        email_verification = await _hunter_email_verification(email)

    # 2.9 Stack Overflow (репутация + top-теги)
    if stackoverflow_user_id:
        stackoverflow_data = await _stackoverflow_profile(stackoverflow_user_id)
        if stackoverflow_data:
            for tag in stackoverflow_data.get("top_tags", []):
                tag_name = (tag.get("tag") or "").lower()
                mapped = _map_topic(tag_name)
                for skill in mapped:
                    if skill not in skills:
                        skills.append(skill)

    # 3. Если навыки не найдены, а репозиториев много — добавим дефолтные по частоте
    if username and not skills and repos_found > 0:
        skills = ["python", "sql", "docker"]

    # 4. Если ничего не найдено — эвристика по локальной части email
    if not skills:
        local_part = email.split("@")[0].lower()
        if re.search(r"python|py", local_part):
            skills.append("python")
        if re.search(r"fastapi|api", local_part):
            skills.append("fastapi")
        if re.search(r"\bgo\b", local_part):
            skills.append("go")
        if re.search(r"js|node", local_part):
            skills.append("nodejs")
        if re.search(r"data|ml|ai", local_part):
            skills.extend(["llm", "ml"])
        if re.search(r"design|ui|ux", local_part):
            skills.extend(["figma", "uiux"])
        if re.search(r"dev|ops|infra", local_part):
            skills.extend(["docker", "kubernetes"])
        if re.search(r"sql|db", local_part):
            skills.extend(["sql", "postgresql"])
        if not skills:
            skills = ["python", "fastapi", "sql", "docker"]

    result = {
        "email": email,
        "github_username": username,
        "skills": skills,
        "source": "github" if username else "local-mock",
        "repos_found": repos_found,
        "profile": profile,
        "contributions": contributions,
        "top_repos": top_repos,
        "linkedin": linkedin_data,
        "stackoverflow": stackoverflow_data,
        "email_verification": email_verification,
        "xing_search": xing_search,
        "cached": False,
        "cache_age_seconds": CACHE_TTL_SECONDS,
    }
    _cache_set(cache_key, result)
    return result
