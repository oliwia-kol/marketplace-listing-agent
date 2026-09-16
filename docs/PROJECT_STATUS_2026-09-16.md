# Stan projektu — 2026-09-16

## Stan

Warstwa lokalna jest gotowa do kontrolowanego testu użytkowego. Workflow, SQLite,
zgody, copy pipeline, worker, MCP, backup, diagnostyka i ograniczony egress mają kod oraz
testy. Live submit pozostaje domyślnie wyłączony.

Projekt nie ma jeszcze dowodu działania na aktualnym, zalogowanym formularzu OLX lub
Allegro Lokalnie. Poziom gotowości to **release candidate do controlled testu**, a nie
zweryfikowana automatyzacja produkcyjna.

## Nowe zabezpieczenia

- proweniencja faktów jest sprawdzana względem trwałej notatki i zapisywana w snapshotcie;
- readback obejmuje pola podstawowe, dostawę, atrybuty i liczbę zdjęć;
- sukces publikacji wymaga konkretnego URL oferty;
- niepewna awaria submitu przechodzi do reconciliation;
- backup odtwarza dane przedmiotu i odrzuca naruszoną sumę kontrolną;
- runtime rozpoznaje aktualne i zmodyfikowane konfiguracje;
- MCP i restart checkpointu mają testy integracyjne;
- research bez skonfigurowanego proxy jest blokowany.

## Dowody

Aktualne wyniki testów i paczki znajdują się w
[`IMPLEMENTATION_LOG_2026-09-16_READINESS.md`](IMPLEMENTATION_LOG_2026-09-16_READINESS.md).
Kontrolowany proxy test: publiczny HTTPS działa, loopback otrzymuje 403. Adaptery LoRA
v2 pozostają poza runtime po negatywnym frozen teście. Końcowy przebieg obejmuje 116
testów, 64% pokrycia instrukcji, czystą instalację wheel, SBOM i audyt zależności bez
znanych podatności.

## Co zostało przed zwykłym użyciem

Pierwsze uruchomienie należy wykonać jako sesję kontrolowaną: prywatny bot, jeden
nieistotny przedmiot, live submit wyłączony, osobny profil Chrome i OLX jako jedyny
portal. Po przejściu restartów i readbacku można używać przygotowania ofert. Publikację
automatyczną wolno oceniać dopiero w osobnym teście dokładnego snapshotu.

Pełny benchmark 120 przypadków × 3 seedy i ocena człowieka pozostają pracą jakościową.
Nie blokują kontrolowanego testu formularza, ale blokują mocne twierdzenie o jakości
opisów dla dowolnej kategorii.
