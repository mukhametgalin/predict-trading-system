"""Configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "trading_system"
    postgres_user: str = "trading"
    postgres_password: str = "changeme123"
    
    # ClickHouse
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_db: str = "markets"
    clickhouse_user: str = "trading"
    clickhouse_password: str = "changeme123"
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    
    # Internal services
    predict_account_url: str = "http://predict-account:8000"
    polymarket_account_url: str = "http://polymarket-account:8000"
    strategy_engine_url: str = "http://strategy-engine:8080"
    
    # Auth
    jwt_secret: str = "super-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    
    @property
    def postgres_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"


settings = Settings()
