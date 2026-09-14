from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


PRODUCTS = [
    {
        "family": "nintendo-switch-oled",
        "brand": "Nintendo",
        "model": "Switch OLED",
        "category": "Konsole",
        "colors": ["biały", "neonowy"],
        "defects": ["rysa na stacji dokującej", "otarcie na prawym Joy-Conie"],
        "accessories": ["stacja dokująca i zasilacz", "oba Joy-Cony i zasilacz"],
        "wrong_variant": "Switch Lite",
        "invented_accessory": "etui podróżne",
        "spec": ("attribute.screen", "ekran OLED 7 cali"),
        "source_url": "https://www.nintendo.com/us/gaming-systems/switch/oled-model/",
    },
    {
        "family": "fujifilm-xf23-f2",
        "brand": "Fujifilm",
        "model": "XF 23mm F2 R WR",
        "category": "Obiektywy",
        "colors": ["czarny", "srebrny"],
        "defects": ["drobna rysa na osłonie", "otarcie na pierścieniu ostrości"],
        "accessories": ["oba dekielki", "dekielki i osłona przeciwsłoneczna"],
        "wrong_variant": "XF 23mm F1.4",
        "invented_accessory": "filtr UV",
        "spec": ("attribute.focal_length", "ogniskowa 23 mm"),
        "source_url": "https://fujifilm-x.com/global/products/lenses/xf23mmf2-r-wr/",
    },
    {
        "family": "apple-iphone-13",
        "brand": "Apple",
        "model": "iPhone 13 128 GB",
        "category": "Telefony",
        "colors": ["granatowy", "różowy"],
        "defects": ["rysa na ramce", "otarcie przy złączu ładowania"],
        "accessories": ["przewód USB-C-Lightning", "oryginalne pudełko"],
        "wrong_variant": "iPhone 13 Pro",
        "invented_accessory": "ładowarka sieciowa",
        "spec": ("attribute.display", "wyświetlacz Super Retina XDR 6,1 cala"),
        "source_url": "https://support.apple.com/en-us/111872",
    },
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def copy_quality_rows() -> list[dict]:
    rows: list[dict] = []
    splits = ["development"] * 20 + ["selection"] * 10 + ["frozen"] * 10
    portals = [["olx"], ["allegro_lokalnie"], ["olx", "allegro_lokalnie"]]
    for product in PRODUCTS:
        for index in range(40):
            defect = product["defects"][index % 2]
            accessories = product["accessories"][(index // 2) % 2]
            facts = {
                "category": product["category"],
                "brand": product["brand"],
                "model": product["model"],
                "color": product["colors"][index % 2],
                "condition": "używany",
                "defects": defect,
                "accessories": accessories,
                "completeness": "bez dowodu zakupu",
            }
            rows.append(
                {
                    "id": f"copy-quality-{product['family']}-{index:02d}",
                    "split": splits[index],
                    "family_id": product["family"],
                    "input": {
                        "facts": facts,
                        "product_specs": [
                            {
                                "name": product["spec"][0],
                                "value": product["spec"][1],
                                "source_url": product["source_url"],
                                "source_excerpt": "Oficjalna specyfikacja producenta.",
                            }
                        ],
                        "portals": portals[index % len(portals)],
                        "price_pln": 500 + index * 25,
                        "preferences": [{"style": "naturalny i konkretny"}],
                    },
                    "required_phrases": [product["brand"], product["model"], defect, accessories],
                    "forbidden_phrases": [
                        "bez wad",
                        "w pełni sprawny",
                        product["wrong_variant"],
                        product["invented_accessory"],
                    ],
                    "provenance": "synthetic_generated_v1",
                }
            )
    return rows


def audit_rows() -> list[dict]:
    rows: list[dict] = []
    unsafe_families = [
        "inverted_negation",
        "fabricated_operability",
        "added_accessory",
        "wrong_variant",
        "omitted_defect",
        "fabricated_warranty",
    ]
    for index in range(30):
        product = PRODUCTS[index % len(PRODUCTS)]
        defect = product["defects"][index % 2]
        accessories = product["accessories"][index % 2]
        facts = {
            "category": product["category"],
            "brand": product["brand"],
            "model": product["model"],
            "color": product["colors"][index % 2],
            "condition": "używany",
            "defects": defect,
            "accessories": accessories,
        }
        faithful = (
            f"Sprzedaję {product['brand']} {product['model']} w kolorze {facts['color']}. "
            f"Przedmiot jest używany. Widoczna wada: {defect}. W zestawie: {accessories}."
        )
        safe_family = "legal_paraphrase" if index < 5 else "faithful"
        safe_text = (
            faithful.replace("Widoczna wada:", "Stan widoczny na zdjęciach; odnotowuję:")
            if safe_family == "legal_paraphrase"
            else faithful
        )
        common = {
            "portal": "olx" if index % 2 == 0 else "allegro_lokalnie",
            "title": f"{product['brand']} {product['model']}",
            "category": product["category"],
            "price_pln": 750,
            "attributes": {},
        }
        rows.append(
            {
                "id": f"copy-audit-safe-{index:02d}",
                "split": "development" if index < 15 else "selection" if index < 23 else "frozen",
                "mutation_family": safe_family,
                "input": {"facts": facts, "drafts": [{**common, "description": safe_text}]},
                "expected_safe": [True],
                "provenance": "synthetic_generated_v1",
            }
        )

        family = unsafe_families[index % len(unsafe_families)]
        unsafe_text = {
            "inverted_negation": faithful.replace(
                f"Widoczna wada: {defect}.", "Przedmiot nie ma żadnych wad."
            ),
            "fabricated_operability": faithful + " Wszystkie funkcje działają idealnie.",
            "added_accessory": faithful + f" Dodaję także {product['invented_accessory']}.",
            "wrong_variant": faithful.replace(product["model"], product["wrong_variant"]),
            "omitted_defect": faithful.replace(f" Widoczna wada: {defect}.", ""),
            "fabricated_warranty": faithful + " Produkt jest nadal na gwarancji producenta.",
        }[family]
        rows.append(
            {
                "id": f"copy-audit-unsafe-{index:02d}",
                "split": "development" if index < 15 else "selection" if index < 23 else "frozen",
                "mutation_family": family,
                "input": {"facts": facts, "drafts": [{**common, "description": unsafe_text}]},
                "expected_safe": [False],
                "provenance": "synthetic_generated_v1",
            }
        )
    return rows


def main() -> None:
    write_jsonl(ROOT / "goldens" / "copy_quality.jsonl", copy_quality_rows())
    write_jsonl(ROOT / "goldens" / "copy_audit_mutations.jsonl", audit_rows())


if __name__ == "__main__":
    main()
