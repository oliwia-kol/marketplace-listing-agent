# 1. Platforma i połączenia

## Pojęcia

- **Orkiestrator** zarządza kolejnością pracy; tu jest nim LangGraph.
- **Kanał** przenosi pytania i decyzje; tu Telegram.
- **Provider inferencji** uruchamia model; tu lokalny serwer Ollama.
- **Browser automation** steruje prawdziwym interfejsem; tu Playwright + Chrome.
- **Checkpointer** zapisuje miejsce procesu; tu SQLite.
- **Repozytorium domenowe** zapisuje przedmiot niezależnie od mechaniki grafu.

LangGraph nie jest modelem i nie steruje Chrome. To automat stanów, który wywołuje
nasze funkcje. Ollama nie zna procesu; odpowiada tylko na jedno zadanie w schemacie.
Telegram nie zawiera reguł biznesowych; tłumaczy przycisk na `accept/edit`.

## Konkretny przykład

Zdjęcie lampy trafia do katalogu lokalnego. Node `analyze_item` prosi model wizualny
o fakty. Node `review_facts` zatrzymuje graf. Telegram pokazuje jedno pole. Kliknięcie
„Akceptuję” nie uruchamia nowego procesu — wznawia istniejący `thread_id`.

## Czytaj kod

- `src/marketplace_agent/runtime.py` — composition root, czyli miejsce łączenia zależności;
- `src/marketplace_agent/workflow/dependencies.py` — jawny kontrakt usług;
- `src/marketplace_agent/channels/telegram.py` — adapter kanału.

## Ćwiczenie

Narysuj wariant z lokalnym web UI zamiast Telegrama. Powinien zmienić się tylko
prostokąt `channels`; jeśli zmieniasz pricing lub model router, naruszyłaś granice.
