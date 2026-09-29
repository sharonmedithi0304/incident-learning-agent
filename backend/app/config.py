import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    hindsight_base_url: str = ""
    hindsight_api_key: str = field(default="", repr=False)  # never printed
    hindsight_bank_id: str = "incident-learning-agent"
    anthropic_api_key: str = field(default="", repr=False)  # never printed
    anthropic_model: str = "claude-sonnet-5"

    @property
    def use_real_hindsight(self) -> bool:
        return bool(self.hindsight_base_url)


def load_settings() -> Settings:
    return Settings(
        hindsight_base_url=os.getenv("HINDSIGHT_BASE_URL", "").strip(),
        hindsight_api_key=os.getenv("HINDSIGHT_API_KEY", "").strip(),
        hindsight_bank_id=os.getenv("HINDSIGHT_BANK_ID", "incident-learning-agent").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5").strip(),
    )
