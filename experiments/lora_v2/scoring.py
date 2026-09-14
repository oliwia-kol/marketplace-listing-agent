from __future__ import annotations

import re


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def score(text: str, facts: dict[str, str]) -> dict[str, float]:
    clean = normalized(re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL))
    values = [normalized(value) for value in facts.values()]
    coverage = sum(value in clean for value in values) / len(values)
    prohibited = ("stan idealny", "bez wad", "w pełni sprawn", "gwaranc")
    unsupported = any(token in clean and token not in " ".join(values) for token in prohibited)
    openers = ("sprzedaję", "na sprzedaż mam", "oferuję", "mam do sprzedania", "wystawiam")
    opening_boundary = all(
        not clean.startswith(opener) or clean.startswith(f"{opener} ") for opener in openers
    )
    return {
        "fact_value_coverage": coverage,
        "item_preservation": float(normalized(facts["item"]) in clean),
        "defect_preservation": float(
            "defects" not in facts or normalized(facts["defects"]) in clean
        ),
        "unsupported_phrase_guard": float(not unsupported),
        "prose_format": float(not clean.startswith("{") and clean.count(".") >= 1),
        "opening_word_boundary": float(opening_boundary),
    }
