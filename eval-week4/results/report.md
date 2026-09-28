# AI Evaluation Report — Week 4 Day 5

## Quality
- answer_accuracy: 0
- average_correctness: 0
- judge_correctness: 0
- judge_relevance: 0
- judge_faithfulness: 0

## Retrieval
- retrieval_precision: 0.1
- retrieval_recall: 0.1
- retrieval_hit_rate: 0.35
- average_faithfulness: 0

## Hallucination / Faithfulness
- hallucination_rate: 1

## Performance
- average_latency_ms: 1.95
- p50_latency_ms: 0.5
- p95_latency_ms: 28

## Token Usage
- total_input_tokens: 0
- total_output_tokens: 0
- average_input_tokens: 0
- average_output_tokens: 0

## Cost
- total_cost_usd: 0
- average_cost_per_request_usd: 0

## Regression Baseline
- answer_accuracy baseline: 0.85 (measured: 0)
- hallucination_rate baseline: 0.1 (measured: 1)
- average_latency_ms baseline: 1200 (measured: 1.95)
- average_cost_per_request_usd baseline: 0.004 (measured: 0)

## Comparison
- answer_accuracy: 0 >= 0.85 -> FAIL
- hallucination_rate: 1 <= 0.1 -> FAIL
- average_latency_ms: 1.95 <= 1500 -> PASS
- average_cost_per_request_usd: 0 <= 0.01 -> PASS
