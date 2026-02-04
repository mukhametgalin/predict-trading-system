package strategies

import (
	"fmt"

	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/types"
	"github.com/rs/zerolog/log"
)

// DeltaNeutralHandler implements delta neutral strategy
// When a fill occurs on one account, immediately place opposite order on paired account
func DeltaNeutralHandler(event types.Event, strategy types.Strategy) ([]types.Command, error) {
	// Only process fill events
	if event.Type != "fill" && event.Type != "trade_executed" {
		return nil, nil
	}

	log.Info().
		Str("strategy", strategy.Name).
		Str("event", event.Type).
		Interface("data", event.Data).
		Msg("Processing event in Delta Neutral strategy")

	// Extract event data
	accountID, _ := event.Data["account_id"].(string)
	accountName, _ := event.Data["account_name"].(string)
	marketID, _ := event.Data["market_id"].(string)
	side, _ := event.Data["side"].(string)
	price, _ := event.Data["price"].(float64)
	shares, _ := event.Data["shares"].(float64)

	if accountID == "" || marketID == "" || side == "" {
		log.Warn().Msg("Missing required fields in event data")
		return nil, nil
	}

	// Get strategy config
	pairs, ok := strategy.Config["pairs"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid pairs config")
	}

	targetPlatform, _ := strategy.Config["target_platform"].(string)
	if targetPlatform == "" {
		targetPlatform = "predict" // Default to predict
	}

	// Find paired account
	var pairedAccountID string
	for _, pairRaw := range pairs {
		pair, ok := pairRaw.(map[string]interface{})
		if !ok {
			continue
		}

		primaryID, _ := pair["primary"].(string)
		hedgeID, _ := pair["hedge"].(string)

		// Check if this account is the primary in a pair
		if primaryID == accountID || primaryID == accountName {
			pairedAccountID = hedgeID
			break
		}
	}

	if pairedAccountID == "" {
		log.Debug().
			Str("account", accountID).
			Msg("Account not found in any pair, skipping")
		return nil, nil
	}

	// Determine opposite side
	oppositeSide := "no"
	if side == "no" {
		oppositeSide = "yes"
	}

	// Check if we should apply price adjustment
	priceAdjustment := 0.0
	if adj, ok := strategy.Config["price_adjustment"].(float64); ok {
		priceAdjustment = adj
	}

	hedgePrice := price + priceAdjustment
	if hedgePrice < 0.01 {
		hedgePrice = 0.01
	}
	if hedgePrice > 0.99 {
		hedgePrice = 0.99
	}

	// Create hedge command
	command := types.Command{
		Type:      "place_order",
		Platform:  targetPlatform,
		AccountID: pairedAccountID,
		MarketID:  marketID,
		Side:      oppositeSide,
		Price:     hedgePrice,
		Shares:    shares,
		Metadata: map[string]interface{}{
			"strategy":        strategy.Name,
			"original_fill":   event.ID,
			"original_account": accountID,
			"original_side":   side,
		},
	}

	log.Info().
		Str("strategy", strategy.Name).
		Str("original_account", accountID).
		Str("hedge_account", pairedAccountID).
		Str("original_side", side).
		Str("hedge_side", oppositeSide).
		Float64("price", hedgePrice).
		Float64("shares", shares).
		Msg("Creating hedge order")

	return []types.Command{command}, nil
}
