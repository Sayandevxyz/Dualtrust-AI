"""
DualTrust AI — Configuration
Reads from environment variables. Fails loudly if required vars are missing.
"""
import os
import json
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # === AI Providers ===
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    MISTRAL_API_KEY: str = Field(default="", description="Mistral API key")
    MISTRAL_OCR_MODEL: str = Field(default="mistral-ocr-latest")
    MISTRAL_STRUCT_MODEL: str = Field(default="mistral-large-latest")

    # === Database ===
    DATABASE_URL: str = Field(default="postgresql://dualtrust:dualtrust_dev@localhost:5432/dualtrust")

    # === Redis ===
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # === Storage ===
    DOCUMENT_STORAGE_PATH: str = Field(default="./storage/documents")
    STORAGE_ENCRYPTION_KEY: str = Field(default="")

    # === Feature Flags ===
    EXTERNAL_VERIFICATION_ENABLED: bool = Field(default=False)
    ASYNC_ANALYSIS: bool = Field(default=True)

    # === App Config ===
    JWT_SECRET: str = Field(default="change_me")
    JWT_EXPIRE_MINUTES: int = Field(default=480)
    DEMO_MODE: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    CONSENSUS_WEIGHTS_PATH: str = Field(default="/app/consensus_weights.json")

    class Config:
        env_file = ".env"
        extra = "ignore"

    def validate_required(self):
        """Fail loudly at startup if critical keys are missing in production; warn in demo mode."""
        errors = []
        if not self.GROQ_API_KEY or self.GROQ_API_KEY == "your_groq_api_key_here":
            errors.append("GROQ_API_KEY is not set")
        if not self.MISTRAL_API_KEY or self.MISTRAL_API_KEY == "your_mistral_api_key_here":
            errors.append("MISTRAL_API_KEY is not set")
        if not self.JWT_SECRET or self.JWT_SECRET == "change_me":
            print("[WARN] JWT_SECRET is using default value — change in production")
        if errors:
            if self.DEMO_MODE:
                print("[DEMO MODE] Running with intelligent heuristic fallback analyzers for unconfigured API keys:")
                for e in errors:
                    print(f"  * {e}")
                print("Live uploaded documents will be processed using simulated dual-pipeline consensus.")
            else:
                raise EnvironmentError(
                    f"DualTrust AI cannot start. Missing required configuration:\n"
                    + "\n".join(f"  * {e}" for e in errors)
                    + "\n\nCopy .env.example to .env and fill in your API keys."
                )

    def get_consensus_weights(self) -> dict:
        """Load consensus weights from config file."""
        paths_to_try = [
            self.CONSENSUS_WEIGHTS_PATH,
            "./consensus_weights.json",
            "../consensus_weights.json",
        ]
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        raise FileNotFoundError(
            f"consensus_weights.json not found. Tried: {paths_to_try}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
