"""環境変数と基本設定の読み込み。"""
import logging
import os
from pathlib import Path
from typing import Literal

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 開発環境で未導入の場合のフォールバック
    load_dotenv = None

logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_PROVIDER: Literal["google", "openai"] = "google"
DEFAULT_MODEL = "gemini-3-pro-preview"


def load_env():
    """backend/.env またはカレントディレクトリの .env を読み込む。"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if load_dotenv:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded backend .env at %s", env_path)
        else:
            load_dotenv()
            logger.info("Loaded .env from current working dir (fallback)")
    else:
        logger.info("python-dotenv 未導入のため .env 読み込みをスキップ")


def get_llm_provider() -> Literal["google", "openai"]:
    """環境変数から LLM プロバイダを取得。未設定ならデフォルト値を使用。"""
    provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider not in ("google", "openai"):
        logger.warning("Invalid LLM_PROVIDER '%s', using default '%s'", provider, DEFAULT_PROVIDER)
        return DEFAULT_PROVIDER
    return provider  # type: ignore


def get_llm_model() -> str:
    """環境変数から LLM モデルを取得。未設定ならデフォルト値を使用。"""
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


_PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "google": "gemini-3-pro-preview",
    "openai": "gpt-4o",
}


def default_model(provider: str) -> str:
    """プロバイダのデフォルトモデル名を返す。"""
    return _PROVIDER_DEFAULT_MODELS.get(provider, DEFAULT_MODEL)
