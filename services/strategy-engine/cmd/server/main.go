package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/config"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/engine"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/eventbus"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/executor"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/storage"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/strategies"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	// Setup logger
	zerolog.TimeFieldFormat = time.RFC3339
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stdout})

	log.Info().Msg("Starting Strategy Engine...")

	// Load config
	cfg := config.Load()

	// Setup storage
	store, err := storage.NewPostgres(cfg.PostgresURL)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to database")
	}
	defer store.Close()

	// Setup event bus
	bus, err := eventbus.NewRedisEventBus(cfg.RedisHost, cfg.RedisPort)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to connect to Redis")
	}
	defer bus.Close()

	// Setup executor
	exec := executor.NewExecutor(
		cfg.PredictAccountURL,
		cfg.PolymarketAccountURL,
	)

	// Create engine
	eng := engine.NewEngine(store, bus, exec)

	// Register strategies
	strategies.RegisterAll(eng)

	// Start engine
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		if err := eng.Start(ctx); err != nil {
			log.Fatal().Err(err).Msg("Engine failed")
		}
	}()

	log.Info().Msg("Strategy Engine started")

	// Wait for interrupt
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	log.Info().Msg("Shutting down...")
	cancel()
	time.Sleep(2 * time.Second)
}
