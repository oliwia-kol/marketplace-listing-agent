from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
SYSTEM = """Napisz krótki, naturalny opis polskiej oferty. Użyj wyłącznie faktów z JSON.
Nie dopisuj parametrów, sprawności, gwarancji ani akcesoriów. Zachowaj każdą podaną
wadę i każdy brak. Brak informacji pomiń. Zwróć sam opis, bez tytułu i komentarza."""

FAMILIES = [
    ("train", "console", "konsolę Nintendo Switch OLED"),
    ("train", "phone", "telefon Samsung Galaxy S23"),
    ("train", "lens", "obiektyw Fujifilm XF 23mm F2"),
    ("train", "monitor", "monitor Dell U2723QE"),
    ("train", "earbuds", "słuchawki AirPods Pro 2"),
    ("train", "curler", "lokówkę Remington CI9532"),
    ("train", "coffee", "ekspres DeLonghi Magnifica S"),
    ("train", "vacuum", "odkurzacz Dyson V8"),
    ("valid", "router", "router TP-Link Archer AX55"),
    ("valid", "mixer", "robot kuchenny Bosch MUM5"),
    ("test", "dryer", "suszarkę do włosów Philips BHD530"),
    ("test", "drill", "wiertarko-wkrętarkę Makita DDF482"),
]

CONDITIONS = ["używany", "w dobrym stanie", "używany kilka razy", "ze śladami używania"]
DEFECTS = ["rysa na obudowie", "otarcie na rogu", "pęknięcie obudowy", "brak"]
ACCESSORIES = ["sam przedmiot", "przewód", "oryginalne pudełko", "bez pudełka"]
OPENERS = ["Sprzedaję", "Na sprzedaż mam", "Oferuję", "Mam do sprzedania", "Wystawiam"]


def make_facts(item: str, index: int) -> dict[str, str]:
    facts = {"item": item}
    mode = index % 10
    if mode != 0:
        facts["condition"] = CONDITIONS[index % len(CONDITIONS)]
    if mode in {2, 3, 5, 7, 9}:
        facts["defects"] = DEFECTS[index % len(DEFECTS)]
    if mode in {3, 4, 6, 8, 9}:
        facts["accessories"] = ACCESSORIES[index % len(ACCESSORIES)]
    if mode in {5, 8}:
        facts["test_scope"] = "użytkowniczka deklaruje, że urządzenie się włącza"
    return facts


def target_text(facts: dict[str, str], index: int) -> str:
    sentences = [f"{OPENERS[index % len(OPENERS)]} {facts['item']}."]
    if value := facts.get("condition"):
        sentences.append(f"Stan: {value}.")
    if value := facts.get("defects"):
        sentences.append(f"Widoczna wada lub informacja o wadach: {value}.")
    if value := facts.get("accessories"):
        sentences.append(f"W zestawie: {value}.")
    if value := facts.get("test_scope"):
        sentences.append(f"Zakres sprawdzenia: {value}.")
    return " ".join(sentences)


def generate(output: Path = ROOT / "data") -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    partitions: dict[str, list[dict]] = {"train": [], "valid": [], "test": []}
    for split, family_id, item in FAMILIES:
        for index in range(50):
            facts = make_facts(item, index)
            partitions[split].append(
                {
                    "id": f"{family_id}-{index:02d}",
                    "family_id": family_id,
                    "provenance": "project_authored_synthetic_lora_v2",
                    "facts": facts,
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {
                            "role": "user",
                            "content": json.dumps(facts, ensure_ascii=False, sort_keys=True)
                            + "\n/no_think",
                        },
                        {"role": "assistant", "content": target_text(facts, index)},
                    ],
                }
            )
    for split, rows in partitions.items():
        (output / f"{split}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        )
    metadata = {
        "seed": 20260914,
        "counts": {split: len(rows) for split, rows in partitions.items()},
        "split_unit": "product_family",
        "families": {
            split: sorted({row["family_id"] for row in rows})
            for split, rows in partitions.items()
        },
        "dataset_sha256": hashlib.sha256(
            b"".join((output / f"{split}.jsonl").read_bytes() for split in partitions)
        ).hexdigest(),
        "human_reviewed": False,
        "private_user_data": False,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata["counts"]


if __name__ == "__main__":
    print(generate())
