"""Telegram Bot Configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    bot_password: str = ""
    web_api_url: str = "http://web-api:8000"
    
    # Authorized users (comma-separated Telegram IDs)
    authorized_users: str = ""
    
    @property
    def authorized_user_ids(self) -> set[int]:
        if not self.authorized_users:
            return set()
        return {int(uid.strip()) for uid in self.authorized_users.split(",") if uid.strip()}
    
    class Config:
        env_file = ".env"


settings = Settings()
