# Marketplace Listing Agent

**Portfolio status: local-first R&D MVP, not a production marketplace bot.**

Human-in-the-loop workflow for evidence-based resale pricing and safe preparation
of marketplace listings. LangGraph coordinates local Ollama models, Playwright and
deterministic security controls; the final Publish action always stays manual.

Lokalny, nadzorowany przez człowieka system agentowy do przygotowywania ofert
sprzedażowych. Zdjęcia i decyzje przychodzą przez Telegram, modele działają w
Ollama, LangGraph utrzymuje stan i punkty akceptacji, a Playwright wypełnia
formularze OLX, Allegro Lokalnie i Vinted. Ostatnie kliknięcie publikacji zawsze
należy do użytkowniczki.

## Co jest zaimplementowane

- graf: zdjęcia → fakty → wybór portali → badanie ceny → osobne teksty → formularze;
- trwałe checkpointy SQLite i akceptacja każdego pola przez `interrupt()`;
- sekwencyjny router lokalnych modeli z fallbackiem i zwalnianiem pamięci;
- zbieranie kandydatów cenowych, weryfikacja stron, audyt porównywalności i statystyka;
- trwały profil Chrome, deterministyczne selektory i wizualny fallback AI;
- twarda blokada kliknięcia publikacji;
- prywatny kanał Telegram z allowlistą jednego `chat_id`;
- wymienne modele, golden datasety i raporty ewaluacyjne;
- profile Fujifilm X, Nintendo Switch/gier i Apple z pułapkami wariantów;
- URL/DNS guard, izolacja prompt injection i kwarantanna niespójnych odczytów;
- testy jednostkowe i integracyjny test całego grafu z atrapami zależności.

## Status uczciwy

Kod i testy lokalne działają. Adaptery żywych formularzy są implementacją beta:
muszą przejść kontrolowane próby na zalogowanych kontach, ponieważ portale zmieniają
DOM, zabezpieczenia i regulaminy. Zestawy `goldens/` to dane startowe syntetyczne —
nie są dowodem jakości produkcyjnej. Lokalne raporty z realnych modeli są podsumowane w [baseline ewaluacji](docs/EVALUATION_RESULTS.md). Dalsza walidacja wymaga prawdziwych, ręcznie oznaczonych zdjęć i prób formularzy na zalogowanych kontach.

## Start

```bash
uv sync --extra dev
cp .env.example .env
uv run marketplace-listing-agent doctor
uv run marketplace-listing-agent configure-token
uv run marketplace-listing-agent eval --suite price_math
uv run marketplace-listing-agent run
```

W `.env` ustaw `MARKETPLACE_AGENT_TELEGRAM_ALLOWED_CHAT_ID`. Token trafia do macOS Keychain,
nie do repozytorium. Modele pobierz zgodnie z [instrukcją](docs/OPERATIONS.md).

## Nauka

Zacznij od [ścieżki kursu](docs/course/00_START.md), potem czytaj kod w kolejności
wskazanej w lekcjach. Pełny obraz decyzji daje [architektura](docs/ARCHITECTURE.md),
a gotowe, uczciwe dowody do portfolio opisuje [portfolio](docs/PORTFOLIO.md).
Zobacz też [profile kategorii](docs/CATEGORY_PLAYBOOKS.md),
[security](docs/SECURITY.md), [baseline ewaluacji](docs/EVALUATION_RESULTS.md) i
[roadmapę](docs/ROADMAP.md).
