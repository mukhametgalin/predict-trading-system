package eventbus

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/mukhametgalin/predict-trading-system/strategy-engine/internal/types"
	"github.com/rs/zerolog/log"
)

type RedisEventBus struct {
	client *redis.Client
}

func NewRedisEventBus(host string, port int) (*RedisEventBus, error) {
	client := redis.NewClient(&redis.Options{
		Addr:         fmt.Sprintf("%s:%d", host, port),
		ReadTimeout:  10 * time.Second, // must be > Block in XREAD
		WriteTimeout: 10 * time.Second,
	})

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	log.Info().Str("addr", fmt.Sprintf("%s:%d", host, port)).Msg("Connected to Redis")

	return &RedisEventBus{client: client}, nil
}

func (b *RedisEventBus) Subscribe(ctx context.Context, streams []string, handler func(types.Event) error) error {
	log.Info().Strs("streams", streams).Msg("Subscribing to streams")

	// Create stream args for XREAD
	args := &redis.XReadArgs{
		Streams: append(streams, make([]string, len(streams))...),
		Block:   5000, // Block for 5 seconds
		Count:   10,
	}

	// Initialize last IDs to "$" (only new messages from now on)
	for i := range streams {
		args.Streams[len(streams)+i] = "$"
	}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			// Read from streams
			result, err := b.client.XRead(ctx, args).Result()
			if err != nil {
				if err == redis.Nil {
					// Timeout, no new messages - continue polling
					continue
				}
				if ctx.Err() != nil {
					return ctx.Err()
				}
				log.Warn().Err(err).Msg("Failed to read from stream, retrying...")
				time.Sleep(time.Second)
				continue
			}

			// Process messages
			for _, stream := range result {
				for _, message := range stream.Messages {
					event, err := b.parseEvent(message)
					if err != nil {
						log.Error().Err(err).Str("stream", stream.Stream).Msg("Failed to parse event")
						continue
					}

					// Handle event
					if err := handler(event); err != nil {
						log.Error().Err(err).Str("event_type", event.Type).Msg("Failed to handle event")
					}

					// Update last ID for this stream
					for i, s := range streams {
						if s == stream.Stream {
							args.Streams[len(streams)+i] = message.ID
						}
					}
				}
			}
		}
	}
}

func (b *RedisEventBus) Publish(ctx context.Context, stream string, event types.Event) error {
	data, err := json.Marshal(event.Data)
	if err != nil {
		return fmt.Errorf("failed to marshal event data: %w", err)
	}

	values := map[string]interface{}{
		"id":        event.ID,
		"type":      event.Type,
		"platform":  event.Platform,
		"timestamp": event.Timestamp.Format(time.RFC3339),
		"data":      string(data),
	}

	if err := b.client.XAdd(ctx, &redis.XAddArgs{
		Stream: stream,
		Values: values,
	}).Err(); err != nil {
		return fmt.Errorf("failed to publish event: %w", err)
	}

	log.Debug().
		Str("stream", stream).
		Str("type", event.Type).
		Msg("Published event")

	return nil
}

func (b *RedisEventBus) parseEvent(msg redis.XMessage) (types.Event, error) {
	// Be tolerant to missing fields. Our publishers may not set "id".
	event := types.Event{
		ID:        msg.ID,
		Type:      "",
		Platform:  "",
		Timestamp: time.Now().UTC(),
		Data:      map[string]interface{}{},
	}

	if v, ok := msg.Values["type"]; ok {
		if s, ok2 := v.(string); ok2 {
			event.Type = s
		}
	}
	if v, ok := msg.Values["platform"]; ok {
		if s, ok2 := v.(string); ok2 {
			event.Platform = s
		}
	}
	if v, ok := msg.Values["timestamp"]; ok {
		if s, ok2 := v.(string); ok2 {
			if t, err := time.Parse(time.RFC3339, s); err == nil {
				event.Timestamp = t
			}
		}
	}
	if v, ok := msg.Values["data"]; ok {
		if s, ok2 := v.(string); ok2 {
			var data map[string]interface{}
			if err := json.Unmarshal([]byte(s), &data); err == nil {
				event.Data = data
			}
		}
	}

	return event, nil
}

func (b *RedisEventBus) Close() error {
	return b.client.Close()
}
