from shared_core.config import BaseAppConfig


class AppConfig(BaseAppConfig):
    """Project-specific configuration extending the shared core settings."""

    APP_NAME: str = "personal-knowledge-base-os"

    # Default markdown vault used by /notes/index when no path is supplied.
    DEFAULT_VAULT_PATH: str = "demo_vault"

    # Embeddings: offline (deterministic hash fallback) unless a key is present.
    # When OPENAI_API_KEY is set the real OpenAI embedding endpoint is used.
    EMBEDDINGS_OFFLINE: bool = True

    # Chat model used when an API key is configured (sim answer otherwise).
    CHAT_MODEL: str = "gpt-4o-mini"

    # Chunking parameters for note ingestion.
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
