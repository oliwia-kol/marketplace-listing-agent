# ADR 0001: lokalne modele i jawny graf

Status: przyjęta hipoteza, do walidacji modelowej.

Kontekst: prywatne zdjęcia, Mac mini M4/24 GB, wiele punktów akceptacji i cel
edukacyjny. Decyzja: Ollama lokalnie, jawny `StateGraph`, modele uruchamiane
sekwencyjnie. Konsekwencje: prywatność inferencji i czytelna architektura kosztem
dłuższego ładowania oraz potencjalnie niższej jakości niż usługi chmurowe. Telegram
pozostaje wyjątkiem od pełnej lokalności transportu zdjęć.
