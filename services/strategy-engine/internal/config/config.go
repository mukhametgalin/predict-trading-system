package config

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	PostgresURL          string
	RedisHost            string
	RedisPort            int
	PredictAccountURL    string
	PolymarketAccountURL string
	LogLevel             string
	DryRun               bool
}

func Load() *Config {
	return &Config{
		PostgresURL: getEnv("POSTGRES_URL", buildPostgresURL()),
		RedisHost:   getEnv("REDIS_HOST", "redis"),
		RedisPort:   getEnvInt("REDIS_PORT", 6379),
		PredictAccountURL: getEnv("PREDICT_ACCOUNT_URL", "http://predict-account:8000"),
		PolymarketAccountURL: getEnv("POLYMARKET_ACCOUNT_URL", "http://polymarket-account:8000"),
		LogLevel:    getEnv("STRATEGY_LOG_LEVEL", "info"),
		DryRun:      getEnvBool("STRATEGY_DRY_RUN", false),
	}
}

func buildPostgresURL() string {
	host := getEnv("POSTGRES_HOST", "postgres")
	db := getEnv("POSTGRES_DB", "trading_system")
	user := getEnv("POSTGRES_USER", "trading")
	pass := getEnv("POSTGRES_PASSWORD", "changeme123")
	
	return fmt.Sprintf("postgres://%s:%s@%s:5432/%s?sslmode=disable", user, pass, host, db)
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if value := os.Getenv(key); value != "" {
		if i, err := strconv.Atoi(value); err == nil {
			return i
		}
	}
	return fallback
}

func getEnvBool(key string, fallback bool) bool {
	if value := os.Getenv(key); value != "" {
		if b, err := strconv.ParseBool(value); err == nil {
			return b
		}
	}
	return fallback
}
