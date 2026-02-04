-- Initialize Delta Neutral Strategy
-- This creates the strategy in the database

INSERT INTO strategies (id, name, active, config, active_accounts, created_at, updated_at)
VALUES (
	'delta-neutral-001',
	'delta_neutral_v1',
	true,
	'{
		"pairs": [
			{
				"primary": "account1",
				"hedge": "account2"
			}
		],
		"target_platform": "predict",
		"price_adjustment": 0.0,
		"max_position_size": 1000,
		"auto_rebalance": true
	}'::jsonb,
	ARRAY['account1', 'account2'],
	NOW(),
	NOW()
)
ON CONFLICT (name) DO UPDATE
SET 
	config = EXCLUDED.config,
	active_accounts = EXCLUDED.active_accounts,
	updated_at = NOW();
