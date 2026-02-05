package executor

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/types"
	"github.com/rs/zerolog/log"
)

type Executor struct {
	predictURL    string
	polymarketURL string
	httpClient    *http.Client
	dryRun        bool
}

func NewExecutor(predictURL, polymarketURL string, dryRun bool) *Executor {
	return &Executor{
		predictURL:    predictURL,
		polymarketURL: polymarketURL,
		dryRun:        dryRun,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (e *Executor) ExecuteCommands(ctx context.Context, commands []types.Command) error {
	for _, cmd := range commands {
		if err := e.executeCommand(ctx, cmd); err != nil {
			log.Error().
				Err(err).
				Str("type", cmd.Type).
				Str("platform", cmd.Platform).
				Str("account", cmd.AccountID).
				Msg("Failed to execute command")
			// Continue with other commands even if one fails
		}
	}
	return nil
}

func (e *Executor) executeCommand(ctx context.Context, cmd types.Command) error {
	switch cmd.Type {
	case "place_order":
		return e.placeOrder(ctx, cmd)
	case "cancel_order":
		return e.cancelOrder(ctx, cmd)
	default:
		return fmt.Errorf("unknown command type: %s", cmd.Type)
	}
}

func (e *Executor) placeOrder(ctx context.Context, cmd types.Command) error {
	baseURL := e.predictURL
	if cmd.Platform == "polymarket" {
		baseURL = e.polymarketURL
	}

	// Build request payload
	payload := map[string]interface{}{
		"account_id": cmd.AccountID,
		"market_id":  cmd.MarketID,
		"side":       cmd.Side,
		"price":      cmd.Price,
		"shares":     cmd.Shares,
		"confirm":    !e.dryRun,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	// Send request
	req, err := http.NewRequestWithContext(
		ctx,
		"POST",
		fmt.Sprintf("%s/trade", baseURL),
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := e.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var errResp map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&errResp)
		return fmt.Errorf("order failed (status %d): %v", resp.StatusCode, errResp)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return err
	}

	log.Info().
		Str("platform", cmd.Platform).
		Str("account", cmd.AccountID).
		Str("market", cmd.MarketID).
		Str("side", cmd.Side).
		Float64("price", cmd.Price).
		Float64("shares", cmd.Shares).
		Interface("result", result).
		Msg("Order placed successfully")

	return nil
}

func (e *Executor) cancelOrder(ctx context.Context, cmd types.Command) error {
	// TODO: Implement cancel order
	log.Warn().Msg("Cancel order not yet implemented")
	return nil
}
