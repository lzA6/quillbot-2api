import os
import json
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class AuthCredential:
    """解析并存储单个 Quillbot 认证凭证"""
    def __init__(self, json_string: str):
        try:
            data = json.loads(json_string)
            self.cookie = data.get("cookie")
            self.token = data.get("token")
            if not self.cookie or not self.token:
                raise ValueError("凭证 JSON 中必须包含 'cookie' 和 'token' 字段。")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"解析认证凭证时出错: {e}")

    def __repr__(self):
        return f"<AuthCredential token_preview='{self.token[:10]}...'>"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "quillbot-2api"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个将 Quillbot AI 图像生成功能转换为兼容 OpenAI 格式 API 的高性能代理。"

    API_MASTER_KEY: Optional[str] = None
    NGINX_PORT: int = 8088
    
    AUTH_CREDENTIALS: List[AuthCredential] = []

    API_REQUEST_TIMEOUT: int = 180
    DEFAULT_MODEL: str = "quillbot-image-default"
    KNOWN_MODELS: List[str] = ["quillbot-image-default"]

    def __init__(self, **values: Any):
        super().__init__(**values)
        # 从环境变量 QUILLBOT_AUTH_1, QUILLBOT_AUTH_2, ... 加载凭证
        i = 1
        while True:
            cred_str = os.getenv(f"QUILLBOT_AUTH_{i}")
            if cred_str:
                try:
                    self.AUTH_CREDENTIALS.append(AuthCredential(cred_str))
                    logger.info(f"成功加载凭证 QUILLBOT_AUTH_{i}")
                except ValueError as e:
                    logger.warning(f"无法加载或解析 QUILLBOT_AUTH_{i}: {e}")
                i += 1
            else:
                break
        
        if not self.AUTH_CREDENTIALS:
            logger.error("错误: 必须在 .env 文件中至少配置一个有效的 QUILLBOT_AUTH_1")
            raise ValueError("未找到任何有效的 Quillbot 认证凭证。")

settings = Settings()
