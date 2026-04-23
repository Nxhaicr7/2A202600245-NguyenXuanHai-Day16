# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_mini.json
- Mode: mock
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.31 | 0.62 | 0.31 |
| Avg attempts | 1 | 2.15 | 1.15 |
| Avg token estimate | 1995.31 | 4919.86 | 2924.55 |
| Avg latency (ms) | 3933.67 | 11019.41 | 7085.74 |

## Failure modes
```json
{
  "wrong_final_answer": 67,
  "none": 93,
  "entity_drift": 1,
  "reflection_overfit": 1,
  "looping": 38
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
