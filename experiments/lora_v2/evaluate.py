from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from mlx_lm import generate, load
from scoring import score


def evaluate(model_name: str, data: Path, output: Path, adapter: str | None) -> None:
    model, tokenizer = load(model_name, adapter_path=adapter)
    results = []
    for raw in data.read_text().splitlines():
        row = json.loads(raw)
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        started = time.perf_counter()
        text = generate(model, tokenizer, prompt=prompt, max_tokens=160, verbose=False)
        results.append(
            {
                "id": row["id"],
                "family_id": row["family_id"],
                "metrics": score(text, row["facts"]),
                "latency_seconds": time.perf_counter() - started,
                "output": text,
            }
        )
    metric_names = results[0]["metrics"]
    payload = {
        "model": model_name,
        "adapter": adapter,
        "test_cases": len(results),
        "metrics": {
            name: statistics.fmean(row["metrics"][name] for row in results)
            for name in metric_names
        },
        "latency_seconds": {
            "median": statistics.median(row["latency_seconds"] for row in results),
            "p95": sorted(row["latency_seconds"] for row in results)[94],
        },
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "data/test.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter")
    args = parser.parse_args()
    evaluate(args.model, args.data, args.output, args.adapter)
