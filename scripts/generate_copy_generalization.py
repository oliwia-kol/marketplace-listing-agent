from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "goldens" / "copy_generalization.jsonl"

FAMILIES = [
    ("development", "console", "konsola", "Nintendo", "Switch OLED"),
    ("development", "phone", "telefon", "Samsung", "Galaxy S23"),
    ("development", "lens", "obiektyw", "Fujifilm", "XF 23mm F2 R WR"),
    ("development", "monitor", "monitor", "Dell", "U2723QE"),
    ("selection", "earbuds", "słuchawki", "Apple", "AirPods Pro 2"),
    ("selection", "curler", "lokówka", "Remington", "CI9532"),
    ("selection", "coffee", "ekspres do kawy", "DeLonghi", "Magnifica S"),
    ("selection", "vacuum", "odkurzacz", "Dyson", "V8"),
    ("frozen", "router", "router", "TP-Link", "Archer AX55"),
    ("frozen", "mixer", "robot kuchenny", "Bosch", "MUM5"),
    ("frozen", "dryer", "suszarka do włosów", "Philips", "BHD530"),
    ("frozen", "drill", "wiertarko-wkrętarka", "Makita", "DDF482"),
]


def scenario_facts(category: str, brand: str, model: str, index: int) -> dict[str, str]:
    base = {"category": category, "brand": brand, "model": model}
    variants = [
        {},
        {"condition": "używany przedmiot"},
        {"condition": "używany", "defects": "rysa na obudowie"},
        {"accessories": "sam przedmiot"},
        {"completeness": "bez oryginalnego pudełka"},
        {
            "condition": "używany kilka razy",
            "attribute.seller_test_claim": "użytkowniczka deklaruje, że urządzenie się włącza",
        },
        {"condition": "stan dobry, normalne ślady używania"},
        {"defects": "jedna funkcja nie była sprawdzana"},
        {"accessories": "przedmiot i przewód widoczne na zdjęciu"},
        {
            "condition": "używany",
            "defects": "otarcie widoczne na zdjęciu",
            "completeness": "brak instrukcji",
        },
    ]
    return base | variants[index]


def generate(destination: Path = DESTINATION) -> int:
    rows = []
    for split, family_id, category, brand, model in FAMILIES:
        for index in range(10):
            facts = scenario_facts(category, brand, model, index)
            rows.append(
                {
                    "id": f"generalization-{family_id}-{index:02d}",
                    "split": split,
                    "family_id": family_id,
                    "scenario": index,
                    "input": {
                        "facts": facts,
                        "portals": ["olx" if index % 2 == 0 else "allegro_lokalnie"],
                        "price_pln": 1,
                        "preferences": [{"style": "naturalny, krótki i konkretny"}],
                    },
                    "forbidden_phrases": [
                        "stan idealny",
                        "bez żadnych wad",
                        "w pełni sprawny",
                        "w pełni sprawna",
                        "wszystkie funkcje działają",
                        "gwarancja",
                    ],
                    "provenance": "project_authored_synthetic_generalization_v1",
                }
            )
    destination.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return len(rows)


if __name__ == "__main__":
    print(f"generated={generate()}")
