-- Initialize Delta Neutral strategy
-- Run after adding test accounts

-- Get account IDs
WITH account_ids AS (
    SELECT 
        (SELECT id FROM accounts WHERE tags @> ARRAY['primary'] LIMIT 1) AS primary_id,
        (SELECT id FROM accounts WHERE tags @> ARRAY['hedge'] LIMIT 1) AS hedge_id
)
INSERT INTO strategies (name, type, config, enabled)
SELECT 
    'Delta Neutral - Test',
    'delta_neutral',
    jsonb_build_object(
        'pairs', jsonb_build_array(
            jsonb_build_object(
                'primary', primary_id::text,
                'hedge', hedge_id::text
            )
        ),
        'target_platform', 'predict',
        'price_adjustment', 0.0,
        'max_position_size', 10.0,
        'max_total_exposure', 10.0
    ),
    false  -- Disabled by default, enable manually
FROM account_ids
WHERE primary_id IS NOT NULL AND hedge_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- Show result
SELECT id, name, type, enabled, config FROM strategies WHERE type = 'delta_neutral';
