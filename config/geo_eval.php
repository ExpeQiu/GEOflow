<?php

/**
 * GEO 策略模块（GEOworkflow 内置，不依赖外部 GEO-OS HTTP）。
 *
 * 设计参考 GEO-OS：strategy → simulate → verify → summary（见 docs/geo-strategy-architecture.md）
 *
 * @see docs/geo-eval-integration.md
 */
return [
    'enabled' => filter_var(env('GEO_EVAL_ENABLED', false), FILTER_VALIDATE_BOOLEAN),
    /** 服务不可用时：skip=标记 skipped 继续；block=标记 failed 阻断发布 */
    'on_unavailable' => in_array(
        strtolower((string) env('GEO_EVAL_ON_UNAVAILABLE', 'skip')),
        ['skip', 'block'],
        true
    ) ? strtolower((string) env('GEO_EVAL_ON_UNAVAILABLE', 'skip')) : 'skip',
    'gate_enabled' => filter_var(env('GEO_EVAL_GATE_ENABLED', false), FILTER_VALIDATE_BOOLEAN),
    'gate_rollout_percent' => max(0, min(100, (int) env('GEO_EVAL_GATE_ROLLOUT_PERCENT', 100))),
    'simulation' => [
        'noise_ratio' => max(1, (int) env('GEO_EVAL_NOISE_RATIO', 100)),
        'mode' => (string) env('GEO_EVAL_SIMULATION_MODE', 'geo_aware'),
        'k' => max(1, min(20, (int) env('GEO_EVAL_SIMULATION_K', 5))),
        'top_k' => max(1, min(20, (int) env('GEO_EVAL_SIMULATION_TOP_K', 5))),
        'llm_provider' => (string) env('GEO_EVAL_LLM_PROVIDER', 'mock'),
        'model_name' => (string) env('GEO_EVAL_MODEL_NAME', 'qwen2.5:14b'),
        'min_rank' => max(1, (int) env('GEO_EVAL_MIN_RANK', 1)),
    ],
    'audit' => [
        'min_brand_hits' => max(0, (int) env('GEO_EVAL_MIN_BRAND_HITS', 0)),
    ],
    'insight' => [
        'fetch_timeout' => max(3, (int) env('GEO_EVAL_INSIGHT_FETCH_TIMEOUT', 12)),
        'user_agent' => (string) env('GEO_EVAL_INSIGHT_USER_AGENT', 'GEOworkflow-Insight/1.0'),
    ],
    'alerts' => [
        'adoption_rate_floor' => (float) env('GEO_EVAL_ALERT_ADOPTION_FLOOR', 0.5),
        'first_position_rate_floor' => (float) env('GEO_EVAL_ALERT_FIRST_POSITION_FLOOR', 0.4),
        'feishu_webhook_url' => trim((string) env('GEO_EVAL_FEISHU_WEBHOOK_URL', '')),
    ],
    'brand_keywords' => array_values(array_filter(array_map(
        'trim',
        explode(',', (string) env('GEO_EVAL_BRAND_KEYWORDS', ''))
    ), static fn (string $v): bool => $v !== '')),
];
