from __future__ import annotations

from collections.abc import Iterable


def classification_metrics(expected: Iterable[bool], actual: Iterable[bool]) -> dict[str, float]:
    pairs = list(zip(expected, actual, strict=True))
    tp = sum(e and a for e, a in pairs)
    tn = sum(not e and not a for e, a in pairs)
    fp = sum(not e and a for e, a in pairs)
    fn = sum(e and not a for e, a in pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": (tp + tn) / len(pairs) if pairs else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def set_metrics(expected: set[str], actual: set[str]) -> dict[str, float]:
    precision = len(expected & actual) / len(actual) if actual else 0.0
    recall = len(expected & actual) / len(expected) if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}
