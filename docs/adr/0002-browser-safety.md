# ADR 0002: Playwright wykonuje, AI tylko planuje

Status: przyjęta.

Kontekst: formularze są zmienne, lecz publikacja ma zawsze należeć do człowieka.
Decyzja: selektory dostępności jako ścieżka podstawowa, model wizualny jako fallback,
zamknięty zestaw akcji, próg confidence, forbidden targets i readback. Konsekwencje:
większa liczba warstw i możliwość zatrzymania na `needs_user`, ale wyraźna granica
uprawnień i testowalne bezpieczeństwo.
