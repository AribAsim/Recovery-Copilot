import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
    NVIDIA_API_URL: str = os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    GROQ_API_URL: str = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./recovery.db")
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", 3))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.70))
    DIAGNOSIS_MODE: str = os.getenv("DIAGNOSIS_MODE", "llm") # "deterministic" | "llm"
    RECOVERY_MAX_WORKERS: int = int(os.getenv("RECOVERY_MAX_WORKERS", 4))
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ]


    # Rough per-action cost in INR, used for net-recovery economics
    ACTION_COST = {
        "retry_payment": 0.0,
        "retry_after_delay": 0.0,
        "send_recovery_message": 0.50,       # SMS cost
        "request_new_payment_method": 0.50,
        "escalate_human": 50.0,
        "give_up": 0.0,
        
        # Legacy/B2B (for backward compatibility)
        "retry_immediate": 0.0,
        "retry_in_24h": 0.0,
        "send_nudge": 0.50,
        "request_new_method": 0.50,
        "send_reminder": 0.50,
        "send_formal_notice": 1.50,
        "escalate_legal_review": 250.0,
    }


settings = Settings()
