from marketplace_agent.research.service import identity_mismatch


def test_model_and_brand_must_be_explicit_in_title() -> None:
    facts = {"brand": "IKEA", "model": "FADO"}
    assert identity_mismatch(facts, "IKEA lampa FADO biała") is None
    assert identity_mismatch(facts, "IKEA lampa stołowa") is not None
    assert identity_mismatch(facts, "Lampa FADO innej marki") is not None


def test_identity_normalization_ignores_punctuation() -> None:
    facts = {"brand": "Dr. Martens", "model": "1460"}
    assert identity_mismatch(facts, "Dr Martens 1460 rozmiar 39") is None
