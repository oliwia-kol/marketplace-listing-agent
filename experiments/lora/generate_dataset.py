from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SYSTEM = """Tworzysz krótki, rzetelny opis polskiego ogłoszenia. Używaj wyłącznie
faktów z JSON. Nie dopisuj sprawności, kompletności, stanu ani zastosowania. Każdą
wadę podaj jasno. Zwróć tylko gotowy opis, bez tytułu i komentarza."""

CATEGORIES = {
    "console": [
        ("Nintendo", "Switch OLED", "biały"),
        ("Nintendo", "Switch OLED", "neonowy"),
        ("Nintendo", "Switch Lite", "turkusowy"),
        ("Nintendo", "Switch Lite", "żółty"),
        ("Nintendo", "Switch V2", "szary"),
        ("Nintendo", "Switch V2", "neonowy"),
        ("Nintendo", "Switch", "szary"),
        ("Nintendo", "Switch", "czerwono-niebieski"),
        ("Nintendo", "Switch Lite", "koralowy"),
        ("Nintendo", "Switch OLED", "czerwony Mario"),
        ("Nintendo", "Switch OLED", "Splatoon 3"),
        ("Nintendo", "Switch OLED", "Zelda"),
        ("Nintendo", "Switch Lite", "niebieski"),
        ("Nintendo", "Switch Lite", "szary"),
        ("Nintendo", "Switch V2", "biały"),
    ],
    "game": [
        ("Nintendo", "Mario Kart 8 Deluxe", "pudełkowa"),
        ("Nintendo", "Animal Crossing New Horizons", "pudełkowa"),
        ("Nintendo", "The Legend of Zelda Tears of the Kingdom", "pudełkowa"),
        ("Nintendo", "Super Mario Odyssey", "pudełkowa"),
        ("Nintendo", "Pokémon Violet", "pudełkowa"),
        ("Nintendo", "Pokémon Legends Arceus", "pudełkowa"),
        ("Nintendo", "Super Smash Bros Ultimate", "pudełkowa"),
        ("Nintendo", "Luigi's Mansion 3", "pudełkowa"),
        ("Nintendo", "Kirby and the Forgotten Land", "pudełkowa"),
        ("Nintendo", "Metroid Dread", "pudełkowa"),
        ("Nintendo", "Pikmin 4", "pudełkowa"),
        ("Nintendo", "Splatoon 3", "pudełkowa"),
        ("Nintendo", "Mario Party Superstars", "pudełkowa"),
        ("Nintendo", "Fire Emblem Engage", "pudełkowa"),
        ("Nintendo", "Xenoblade Chronicles 3", "pudełkowa"),
    ],
    "fuji": [
        ("Fujifilm", "XF 23mm F2 R WR", "czarny"),
        ("Fujifilm", "XF 35mm F2 R WR", "czarny"),
        ("Fujifilm", "XF 50mm F2 R WR", "srebrny"),
        ("Fujifilm", "XF 18-55mm F2.8-4 R LM OIS", "czarny"),
        ("Fujifilm", "XF 16-80mm F4 R OIS WR", "czarny"),
        ("Fujifilm", "XF 27mm F2.8 R WR", "czarny"),
        ("Fujifilm", "XF 56mm F1.2 R", "czarny"),
        ("Fujifilm", "XC 15-45mm F3.5-5.6 OIS PZ", "srebrny"),
        ("Fujifilm", "X-T30 II", "srebrny"),
        ("Fujifilm", "X-S10", "czarny"),
        ("Fujifilm", "X-T5", "czarny"),
        ("Fujifilm", "X100V", "srebrny"),
        ("Fujifilm", "X-E4", "czarny"),
        ("Fujifilm", "XF 10-24mm F4 R OIS WR", "czarny"),
        ("Fujifilm", "XF 70-300mm F4-5.6 R LM OIS WR", "czarny"),
    ],
    "apple": [
        ("Apple", "iPhone 15 Pro 256 GB", "tytan naturalny"),
        ("Apple", "iPhone 14 128 GB", "północ"),
        ("Apple", "iPhone 13 mini 128 GB", "niebieski"),
        ("Apple", "MacBook Air M2 16/256 GB", "północ"),
        ("Apple", "MacBook Air M1 8/256 GB", "srebrny"),
        ("Apple", "MacBook Pro 14 M3 Pro 18/512 GB", "gwiezdna czerń"),
        ("Apple", "iPad Air 5 64 GB Wi-Fi", "niebieski"),
        ("Apple", "iPad mini 6 64 GB Wi-Fi", "gwiezdna szarość"),
        ("Apple", "Apple Watch Series 9 45 mm", "północ"),
        ("Apple", "AirPods Pro 2 USB-C", "biały"),
        ("Apple", "Magic Keyboard", "biały"),
        ("Apple", "Magic Mouse", "czarny"),
        ("Apple", "Mac mini M2 8/256 GB", "srebrny"),
        ("Apple", "iPhone 15 128 GB", "różowy"),
        ("Apple", "iPad Pro 11 M2 128 GB", "gwiezdna szarość"),
    ],
}

SCENARIOS = [
    ("używany", "drobne rysy na obudowie", "oryginalne pudełko"),
    ("bardzo dobry", "otarcie na jednym rogu", "pudełko i przewód"),
    ("dobry", "widoczne ślady użytkowania", "sam przedmiot"),
    ("używany", "rysa widoczna na zdjęciu", "przewód zasilający"),
    ("dobry", "uszkodzone opakowanie", "oryginalne opakowanie"),
]


def target_text(facts: dict[str, str]) -> str:
    return (
        f"Sprzedaję {facts['brand']} {facts['model']}. Kolor lub wariant: {facts['color']}. "
        f"Stan: {facts['condition']}. Wada lub ślad użytkowania: {facts['defects']}. "
        f"W zestawie: {facts['accessories']}."
    )


def generate(output: Path) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    rows = {"train": [], "valid": [], "test": []}
    family_index = 0
    for category, families in CATEGORIES.items():
        for brand, model, color in families:
            split = (
                "train"
                if family_index % 10 < 8
                else ("valid" if family_index % 10 == 8 else "test")
            )
            # Variant (including color/edition) is the split unit; all five condition
            # scenarios for that exact product variant stay in one partition.
            family_id = hashlib.sha256(
                f"{category}:{brand}:{model}:{color}".encode()
            ).hexdigest()[:12]
            for scenario_index, (condition, defects, accessories) in enumerate(SCENARIOS):
                facts = {
                    "category": category,
                    "brand": brand,
                    "model": model,
                    "color": color,
                    "condition": condition,
                    "defects": defects,
                    "accessories": accessories,
                }
                rows[split].append(
                    {
                        "id": f"{family_id}-{scenario_index}",
                        "family_id": family_id,
                        "provenance": "synthetic_rule_generated_v1",
                        "facts": facts,
                        "messages": [
                            {"role": "system", "content": SYSTEM},
                            {
                                "role": "user",
                                "content": (
                                    json.dumps(facts, ensure_ascii=False, sort_keys=True)
                                    + "\n/no_think"
                                ),
                            },
                            {"role": "assistant", "content": target_text(facts)},
                        ],
                    }
                )
            family_index += 1
    for split, values in rows.items():
        with (output / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for value in values:
                handle.write(json.dumps(value, ensure_ascii=False) + "\n")
    metadata = {
        "seed": 20260913,
        "generator": "generate_dataset.py",
        "license": "project-authored synthetic data; Apache-2.0 repository license",
        "counts": {key: len(value) for key, value in rows.items()},
        "split_unit": "family_id",
        "private_user_data": False,
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata["counts"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data")
    print(generate(parser.parse_args().output))
