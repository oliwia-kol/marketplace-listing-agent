# Stan projektu — 2026-09-13

## Ocena wykonawcza

Projekt ma kompletną lokalną architekturę MVP: trwały workflow, research i pricing,
warstwy walidacji modeli, niezmienne snapshoty, dwie zgody, kolejkę wykonawczą,
interwencje, kontrolowany submit, monitoring, MCP, backup, CI oraz materiały
edukacyjne. Nie ma jeszcze dowodu działania na zalogowanych formularzach ani dowodu
rzeczywistej publikacji. Te dwie granice są celowo oddzielone od testów automatycznych.

- checkout: `/Users/oliwia/Desktop/shopper-bot`;
- branch: `codex/implementation-a2`;
- baza implementacji: `a8b9862`;
- zdalny GitHub: niezmieniony;
- realne portale: niczego nie opublikowano;
- prywatne dane i adapter LoRA: nie są przeznaczone do Git.

## Stan etapów planu

| Etap | Stan 13.09 | Dowód | Co pozostaje |
|---|---|---|---|
| E0 baseline i higiena | wykonany lokalnie | manifest, datowana notatka, walidacje config | ustalić docelowy `main` przy publikacji |
| E1 research i cena | wykonany dla publicznych danych | fixtures, bramka, 20/20 comparables i price | ręcznie sprawdzona seria live dla własnych kategorii |
| E2 formularze bez submit | zaimplementowany i testowany na doubles | exact labels, readback, screenshot, fail closed | inventory zalogowanego OLX i Allegro Lokalnie |
| E3 paczkowanie i doctor | wykonany | czysty wheel/Python 3.12, core doctor | uruchomić doctor z realnym Telegramem i Chrome |
| E4 GitHub Actions | skonfigurowany | workflow, Dependabot, secret scan | push i pierwszy rzeczywisty run GitHub Actions |
| E5 kontekst i akceptacje | wykonany lokalnie | SQLite v3, restart, snapshot/hash, one-time token | test ręczny przez Telegram po restarcie Maca |
| E6 monitoring i ewaluacja | wykonany dla danych syntetycznych | RunEvent, HTML, 120 goldenów, raporty | realne zanonimizowane obrazy i ręczne etykiety |
| E7 worker i interwencje | wykonany lokalnie | atomowy claim, watchdog, CAPTCHA/login/fee states | controlled-browser test |
| E8 Docker | wykonany dla granicy infrastruktury | build, core doctor, public przez proxy, private/direct blocked | zastąpić diagnostyczny research-worker pełnym procesem researchu |
| E9 publikacja OLX | kod gotowy do próby kontrolowanej | druga zgoda, readback, exact submit, `unknown` | preferować oficjalne API po akceptacji aplikacji; live test |
| E10 MCP | wykonany lokalnie | MCP SDK v2, stdio, wąskie narzędzia i testy | podłączyć wybranego hosta MCP |
| E11 Allegro Lokalnie | kod gotowy do próby kontrolowanej | osobna specyfikacja, submit `Wystaw` | live inventory; oficjalne API nie obsługuje Lokalnie |
| E12 LoRA | eksperyment zakończony | trening MLX, baseline, frozen test, hashe | nie integrować bez realnych danych i semantic eval |

## Zweryfikowane wyniki

- Ruff: passed.
- Pytest: **85 passed**.
- Coverage: **59%** całego pakietu; kluczowe moduły domenowe mają 87–98%.
- Testy z `ResourceWarning`: passed bez niezamkniętych połączeń SQLite.
- JSONL: 120 unikalnych przypadków, po 20 na sześć suite'ów.
- Wheel: zbudowany i zainstalowany poza checkoutem w czystym Pythonie 3.12.
- Installed CLI: `doctor --scope core` passed.
- Installed MCP: serwer skonstruowany jako `MCPServer`.
- Pliki LaunchAgent: oba szablony przeszły `plutil -lint`; skrypty przeszły `zsh -n`.
- Compose: `docker compose config` passed.
- Docker: daemon `29.4.0` (Linux/aarch64 VM), build obu obrazów i core doctor w
  kontenerze przeszły. Publiczny HTTPS przez proxy zwrócił 200, localhost został
  odrzucony (`ProxyError`), a bezpośrednie wyjście workera (`trust_env=False`) zostało
  zablokowane (`ConnectError`).

## Najważniejsze wyniki modeli

| Suite | Model/warstwa | Wynik | Znaczenie |
|---|---|---:|---|
| price math | kod | 20/20 | deterministyczna statystyka |
| comparables | Qwen3.5 9B | 20/20 | dobry wynik syntetyczny |
| forms | Qwen3.5 4B | 20/20 | bez niedozwolonych kliknięć |
| copy audit | Qwen3.5 9B | 15/20 | pięć naruszeń dokładnej liczby portali |
| raw copy | Bielik 11B v3 | 7/20 | nie nadaje się bez guardów i fallbacku |
| facts | Qwen3.5 9B | 14/20 | poprawna struktura i brak zakazanych halucynacji, lecz HITL pozostaje obowiązkowy |

## Ryzyka otwarte

1. Aktualne kontrolki zalogowanych formularzy nie zostały zinwentaryzowane. Kod ma
   zachowanie fail closed, ale to nie jest dowód kompatybilności z portalem.
2. Browser submit istnieje, lecz jest domyślnie wyłączony. Nie testowano skutku na
   realnym koncie.
3. Oficjalny OLX Partner API jest lepszym celem długoterminowym, ale wymaga rejestracji
   i akceptacji aplikacji. Nie implementujemy tokenów na podstawie domysłów.
4. Docker research boundary została sprawdzona w działaniu. Worker kontenerowy jest
   jednak scaffoldem diagnostycznym, nie pełnym deploymentem researchu.
5. Goldeny są syntetyczne. Brakuje zatwierdzonego zbioru realnych zdjęć i ofert.
6. Guardy językowe zmniejszają znane ryzyko, lecz nie dowodzą pełnego rozumienia
   semantycznego każdej polskiej parafrazy.
7. CI istnieje w repozytorium, ale dopóki zmiana nie trafi na GitHub, nie ma zdalnego
   zielonego runu ani badge'a.

## Następne bramki operacyjne

1. Skonfigurować prywatny bot Telegram i wykonać restart test bez publikacji.
2. Zalogować się ręcznie do izolowanego profilu sprzedażowego i wykonać inventory pól
   OLX oraz Allegro Lokalnie, zatrzymując się przed submit.
3. Zarejestrować aplikację w OLX Developer Portal; po akceptacji porównać API z browser
   adapterem i wybrać API jako preferowaną ścieżkę OLX.
4. Zebrać zanonimizowane, ręcznie etykietowane przypadki realne; dopiero potem powtórzyć
   wybór modeli i rozważyć drugi eksperyment LoRA.
5. Przed publicznym repo wykonać privacy/history audit, zaakceptować opis CV i osobno
   autoryzować push.
