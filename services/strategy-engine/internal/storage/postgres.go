package storage

import (
	"database/sql"
	"encoding/json"
	"fmt"

	_ "github.com/lib/pq"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/types"
	"github.com/rs/zerolog/log"
)

type PostgresStorage struct {
	db *sql.DB
}

func NewPostgres(url string) (*PostgresStorage, error) {
	db, err := sql.Open("postgres", url)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Create tables if not exist
	if err := createTables(db); err != nil {
		return nil, fmt.Errorf("failed to create tables: %w", err)
	}

	log.Info().Msg("Connected to PostgreSQL")

	return &PostgresStorage{db: db}, nil
}

func createTables(db *sql.DB) error {
	// Tables are created by init.sql, just verify connection
	return nil
}

func (s *PostgresStorage) GetActiveStrategies() ([]types.Strategy, error) {
	query := `
		SELECT id, name, type, enabled, config, created_at, updated_at
		FROM strategies
		WHERE enabled = true
	`

	rows, err := s.db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var strategies []types.Strategy
	for rows.Next() {
		var strategy types.Strategy
		var configJSON []byte

		err := rows.Scan(
			&strategy.ID,
			&strategy.Name,
			&strategy.Type,
			&strategy.Active,
			&configJSON,
			&strategy.CreatedAt,
			&strategy.UpdatedAt,
		)
		if err != nil {
			log.Error().Err(err).Msg("Failed to scan strategy")
			continue
		}

		// Parse config
		if err := json.Unmarshal(configJSON, &strategy.Config); err != nil {
			log.Error().Err(err).Str("strategy", strategy.Name).Msg("Failed to parse config")
			continue
		}

		strategies = append(strategies, strategy)
	}

	return strategies, nil
}

func (s *PostgresStorage) GetStrategy(id string) (*types.Strategy, error) {
	query := `
		SELECT id, name, type, enabled, config, created_at, updated_at
		FROM strategies
		WHERE id = $1::uuid
	`

	var strategy types.Strategy
	var configJSON []byte

	err := s.db.QueryRow(query, id).Scan(
		&strategy.ID,
		&strategy.Name,
		&strategy.Type,
		&strategy.Active,
		&configJSON,
		&strategy.CreatedAt,
		&strategy.UpdatedAt,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	// Parse config
	if err := json.Unmarshal(configJSON, &strategy.Config); err != nil {
		return nil, err
	}

	return &strategy, nil
}

func (s *PostgresStorage) Close() error {
	return s.db.Close()
}
