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
		Addr: fmt.Sprintf("%s:%d", host, port),
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
		Block:   0, // Block indefinitely
		Count:   10,
	}

	// Initialize last IDs to ">" (only new messages)
	for i := range streams {
		args.Streams[len(streams)+i] = ">"
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
					continue
				}
				log.Error().Err(err).Msg("Failed to read from stream")
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
	event := types.Event{
		ID:       msg.Values["id"].(string),
		Type:     msg.Values["type"].(string),
		Platform: msg.Values["platform"].(string),
	}

	if ts, ok := msg.Values["timestamp"].(string); ok {
		t, err := time.Parse(time.RFC3339, ts)
		if err == nil {
			event.Timestamp = t
		}
	}

	if dataStr, ok := msg.Values["data"].(string); ok {
		var data map[string]interface{}
		if err := json.Unmarshal([]byte(dataStr), &data); err == nil {
			event.Data = data
		}
	}

	return event, nil
}

func (b *RedisEventBus) Close() error {
	return b.client.Close()
}
