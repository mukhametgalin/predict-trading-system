package strategies

import "github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/engine"

// RegisterAll registers all available strategies
func RegisterAll(eng *engine.Engine) {
	// Register Delta Neutral strategy
	eng.RegisterStrategy("delta_neutral", DeltaNeutralHandler)
	eng.RegisterStrategy("delta_neutral_v1", DeltaNeutralHandler)
	
	// Future strategies can be registered here
	// eng.RegisterStrategy("arbitrage", ArbitrageHandler)
	// eng.RegisterStrategy("momentum", MomentumHandler)
}
