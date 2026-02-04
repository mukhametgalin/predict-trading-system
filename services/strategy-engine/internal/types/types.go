package types

import "time"

// Event represents an event from the event bus
type Event struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"`      // fill, cancel, error, market_update
	Platform  string                 `json:"platform"`  // predict, polymarket
	Timestamp time.Time              `json:"timestamp"`
	Data      map[string]interface{} `json:"data"`
}

// Command represents a command to execute
type Command struct {
	Type      string                 `json:"type"`      // place_order, cancel_order
	Platform  string                 `json:"platform"`  // predict, polymarket
	AccountID string                 `json:"account_id"`
	MarketID  string                 `json:"market_id"`
	Side      string                 `json:"side"`      // yes, no
	Price     float64                `json:"price"`
	Shares    float64                `json:"shares"`
	Metadata  map[string]interface{} `json:"metadata"`
}

// Strategy represents a trading strategy
type Strategy struct {
	ID              string                 `json:"id"`
	Name            string                 `json:"name"`
	Active          bool                   `json:"active"`
	Config          map[string]interface{} `json:"config"`
	ActiveAccounts  []string               `json:"active_accounts"`
	CreatedAt       time.Time              `json:"created_at"`
	UpdatedAt       time.Time              `json:"updated_at"`
}

// StrategyHandler is the function signature for strategy handlers
type StrategyHandler func(event Event, strategy Strategy) ([]Command, error)

// Position represents an account position
type Position struct {
	AccountID  string    `json:"account_id"`
	Platform   string    `json:"platform"`
	MarketID   string    `json:"market_id"`
	OutcomeID  string    `json:"outcome_id"`
	Side       string    `json:"side"`
	Shares     float64   `json:"shares"`
	AvgPrice   float64   `json:"avg_price"`
	UpdatedAt  time.Time `json:"updated_at"`
}
