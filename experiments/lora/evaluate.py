from __future__ import annotations

import argparse
import json
import platform
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

from mlx_lm import generate, load


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def metrics(output: str, row: dict) -> dict[str, float]:
    visible_output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)
    text = normalized(visible_output)
    facts = row["facts"]
    check_fields = ("brand", "model", "color", "condition", "defects", "accessories")
    coverage = sum(normalized(str(facts[field])) in text for field in check_fields) / len(
        check_fields
    )
    unsupported = []
    for phrase in ("w pełni sprawny", "bez wad", "jak nowy", "stan idealny"):
        if phrase in text and phrase not in normalized(" ".join(map(str, facts.values()))):
            unsupported.append(phrase)
    reference = row["messages"][-1]["content"]
    return {
        "fact_value_coverage": coverage,
        "defect_preservation": float(normalized(facts["defects"]) in text),
        "unsupported_phrase_guard": float(not unsupported),
        "reference_similarity": SequenceMatcher(None, normalized(reference), text).ratio(),
        "no_think_markup": float("<think>" not in text),
        "prose_format": float(
            not text.startswith("{") and "sprzedaję" in text and text.count(".") >= 3
        ),
    }


def evaluate(model_name: str, data_path: Path, output_path: Path, adapter: str | None) -> None:
    model, tokenizer = load(model_name, adapter_path=adapter)
    results = []
    for line in data_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        started = time.perf_counter()
        generated = generate(model, tokenizer, prompt=prompt, max_tokens=180, verbose=False)
        results.append(
            {
                "id": row["id"],
                "family_id": row["family_id"],
                "metrics": metrics(generated, row),
                "latency_seconds": time.perf_counter() - started,
                "output": generated,
            }
        )
    names = results[0]["metrics"]
    summary = {
        name: sum(result["metrics"][name] for result in results) / len(results) for name in names
    }
    payload = {
        "model": model_name,
        "adapter": adapter,
        "test_cases": len(results),
        "environment": {"python": platform.python_version(), "machine": platform.machine()},
        "metrics": summary,
        "mean_latency_seconds": sum(result["latency_seconds"] for result in results) / len(results),
        "results": results,
        "limitations": [
            "String metrics cannot detect every semantically unsupported claim.",
            "All examples are synthetic and need later validation on approved real examples.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "data/test.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter")
    args = parser.parse_args()
    evaluate(args.model, args.data, args.output, args.adapter)
