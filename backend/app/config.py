"""Settings read from environment variables. Nothing here has a secret default."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a local .env file without overriding real env vars."""
    for candidate in (REPO_DIR / ".env", BACKEND_DIR / ".env"):
        if not candidate.is_file():
            continue
        for raw in candidate.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_api_key: str | None
    llm_model: str
    llm_effort: str
    cookie_secure: bool
    session_days: int
    max_import_bytes: int
    max_import_messages: int
    frontend_dist: Path
    cors_origins: list[str] = field(default_factory=list)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


def get_settings() -> Settings:
    _load_dotenv()
    default_db = BACKEND_DIR / "data" / "summa.db"
    origins = [o.strip() for o in os.environ.get("SUMMA_CORS_ORIGINS", "").split(",") if o.strip()]
    return Settings(
        database_url=os.environ.get("DATABASE_URL", f"sqlite:///{default_db}"),
        llm_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        llm_model=os.environ.get("SUMMA_LLM_MODEL", "claude-opus-5-5"),
        llm_effort=os.environ.get("SUMMA_LLM_EFFORT", "medium"),
        cookie_secure=_bool("SUMMA_COOKIE_SECURE", False),
        session_days=int(os.environ.get("SUMMA_SESSION_DAYS", "14")),
        max_import_bytes=int(os.environ.get("SUMMA_MAX_IMPORT_BYTES", str(2 * 1024 * 1024))),
        max_import_messages=int(os.environ.get("SUMMA_MAX_IMPORT_MESSAGES", "5000")),
        frontend_dist=Path(os.environ.get("SUMMA_FRONTEND_DIST", str(REPO_DIR / "frontend" / "dist"))),
        cors_origins=origins,
    )


settings = get_settings()
