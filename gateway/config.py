"""Configuration helpers for the WeChat/Feishu gateway service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal
from pathlib import Path

# Load .env file if exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed


@dataclass(frozen=True)
class GatewayConfig:
    """Runtime configuration loaded from environment variables."""

    # Gateway settings
    channel_type: Literal["wechat", "feishu"] = "feishu"
    listen_host: str = "0.0.0.0"
    listen_port: int = 8099
    access_token: str | None = None
    
    # Feishu settings
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_verification_token: str | None = None

    @classmethod
    def load(cls) -> "GatewayConfig":
        channel_type = os.getenv("CHANNEL_TYPE", "feishu")
        host = os.getenv("GATEWAY_HOST", "0.0.0.0")
        port = int(os.getenv("GATEWAY_PORT", "8099"))
        token = os.getenv("GATEWAY_TOKEN")
        
        # Feishu configuration
        feishu_app_id = os.getenv("FEISHU_APP_ID")
        feishu_app_secret = os.getenv("FEISHU_APP_SECRET")
        feishu_verification_token = os.getenv("FEISHU_VERIFICATION_TOKEN")
        
        return cls(
            channel_type=channel_type,
            listen_host=host,
            listen_port=port,
            access_token=token,
            feishu_app_id=feishu_app_id,
            feishu_app_secret=feishu_app_secret,
            feishu_verification_token=feishu_verification_token,
        )
