package engine

import (
	"context"
	"fmt"
	"sync"

	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/eventbus"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/executor"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/storage"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/types"
	"github.com/rs/zerolog/log"
)

type Engine struct {
	storage   *storage.PostgresStorage
	eventBus  *eventbus.RedisEventBus
	executor  *executor.Executor
	handlers  map[string]types.StrategyHandler
	mu        sync.RWMutex
}

func NewEngine(
	storage *storage.PostgresStorage,
	eventBus *eventbus.RedisEventBus,
	executor *executor.Executor,
) *Engine {
	return &Engine{
		storage:  storage,
		eventBus: eventBus,
		executor: executor,
		handlers: make(map[string]types.StrategyHandler),
	}
}

func (e *Engine) RegisterStrategy(name string, handler types.StrategyHandler) {
	e.mu.Lock()
	defer e.mu.Unlock()
	
	e.handlers[name] = handler
	log.Info().Str("strategy", name).Msg("Registered strategy handler")
}

func (e *Engine) Start(ctx context.Context) error {
	log.Info().Msg("Starting strategy engine...")

	// Load active strategies from database
	strategies, err := e.storage.GetActiveStrategies()
	if err != nil {
		return fmt.Errorf("failed to load strategies: %w", err)
	}

	log.Info().Int("count", len(strategies)).Msg("Loaded active strategies")

	// Subscribe to event streams
	streams := []string{
		"fill_events",
		"trade_events",
		"account_events",
	}

	return e.eventBus.Subscribe(ctx, streams, func(event types.Event) error {
		return e.handleEvent(ctx, event, strategies)
	})
}

func (e *Engine) handleEvent(
	ctx context.Context,
	event types.Event,
	strategies []types.Strategy,
) error {
	log.Debug().
		Str("type", event.Type).
		Str("platform", event.Platform).
		Msg("Received event")

	// Process event through all active strategies
	for _, strategy := range strategies {
		if !strategy.Active {
			continue
		}

		// Get handler for this strategy
		e.mu.RLock()
		handler, exists := e.handlers[strategy.Type]
		e.mu.RUnlock()

		if !exists {
			log.Warn().
				Str("strategy", strategy.Name).
				Str("type", strategy.Type).
				Msg("No handler registered for strategy type")
			continue
		}

		// Execute strategy handler
		commands, err := handler(event, strategy)
		if err != nil {
			log.Error().
				Err(err).
				Str("strategy", strategy.Name).
				Msg("Strategy handler failed")
			continue
		}

		if len(commands) == 0 {
			continue
		}

		// Execute commands
		log.Info().
			Str("strategy", strategy.Name).
			Int("commands", len(commands)).
			Msg("Executing commands from strategy")

		if err := e.executor.ExecuteCommands(ctx, commands); err != nil {
			log.Error().
				Err(err).
				Str("strategy", strategy.Name).
				Msg("Failed to execute commands")
		}
	}

	return nil
}
