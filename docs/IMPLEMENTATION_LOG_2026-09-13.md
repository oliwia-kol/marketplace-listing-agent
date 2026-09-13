# Dziennik implementacji — 2026-09-13

## Zakres wykonany

- przeniesiono dane runtime do prywatnego katalogu aplikacji i dołączono domyślne
  configi/goldeny do wheel;
- dodano wielozakresowy `doctor`, bezpieczny manifest środowiska i backup/restore;
- skonfigurowano CI, Dependabot, lint, testy, walidację JSONL, skan sekretów, build i
  smoke test wheel;
- wdrożono SQLite schema v3: rozmowa, snapshoty, zgody, joby, interwencje i telemetry;
- związano jednorazową zgodę z użytkownikiem, krokiem, przedmiotem i konkretnymi
  snapshotami; zmiana treści unieważnia pending approval;
- wydzielono worker formularzy od orkiestratora i ograniczono go do `job_id`;
- dodano dwufazowy przebieg prepare/readback oraz osobną zgodę na submit;
- dodano recovery lease: stary prepare wraca do kolejki, stary submit przechodzi do
  `unknown` bez retry;
- ponowiono hash zdjęć tuż przed publikacją i wymuszono readback wszystkich oczekiwanych
  pól biznesowych;
- wprowadzono timeout wywołań modeli per rola;
- rozszerzono guard opisów o twierdzenia o sprawności, kompletności i akcesoriach
  zaobserwowane w benchmarku;
- wdrożono lokalny MCP v2 po stdio z wąskimi narzędziami;
- przygotowano Docker/Compose oraz proxy egress odrzucający prywatne adresy;
- przeprowadzono realny trening LoRA na M4 i porównano z baseline oraz szablonem;
- przygotowano podręcznik, walkthrough, laboratoria, macierz kompetencji, ADR-y i atlas
  awarii modeli.

## Znalezione i naprawione problemy

1. Editable install w Pythonie 3.14 pozwalał testom przejść, choć zainstalowane CLI nie
   widziało zasobów jak produkt. CI i smoke test używają teraz non-editable wheel.
2. `with sqlite3.connect(...)` wykonuje commit/rollback, lecz samo nie zamyka połączenia.
   Dodano context manager gwarantujący `close`; test z ResourceWarning jest czysty.
3. Worker nie miał reguły na śmierć procesu. Dodano bezpiecznie asymetryczny watchdog.
4. Zdjęcia sprawdzano podczas prepare, ale nie ponownie bezpośrednio przed submit.
5. Router nie ograniczał czasu jednego wywołania modelu.
6. Pierwsza wersja rozszerzonych goldenów miała błąd ontologii: format gry opisano jako
   kolor, a storage Apple niespójnie włączono do nazwy modelu. Etykiety poprawiono i
   benchmark uruchomiono ponownie.
7. Bielik dopisywał działanie, wpływ wady i akcesoria. To potwierdziło potrzebę
   niezależnego audytu oraz deterministycznego fallbacku.

## LoRA — wykonanie

- host: Apple Silicon M4, 24 GB RAM;
- framework: MLX-LM 0.30.7, MLX 0.32.2;
- baza: `Qwen/Qwen3-0.6B`;
- dane: 240 train, 30 validation, 30 frozen test;
- konfiguracja: ostatnie 8 warstw, batch 1, accumulation 4, LR 1e-5, 200 iteracji,
  context 512, prompt masking, gradient checkpointing;
- parametry trenowane: 1,442 mln / 596,050 mln = 0,242%;
- peak memory: 1,797 GB;
- validation loss: 2,580 na początku i 0,005 przy iteracji 200;
- adapter: 5 779 075 bajtów;
- SHA-256: `4466df16b28fd00879aceb13e263184b7c111ddd3b41ab1dbf26d176dc5b2da4`;
- frozen test: LoRA 30/30 w wąskim zadaniu, ale deterministyczny szablon także 30/30;
- decyzja: adapter pozostaje eksperymentem, nie modelem domyślnym.

## Komentarze i wątpliwości

- Spadek loss pokazuje dopasowanie optymalizacji, nie gwarantuje generalizacji.
- 120 goldenów spełnia minimum ilościowe, ale jakość produkcyjna wymaga realnych,
  ręcznie etykietowanych danych i obrazów.
- Wysoki wynik planowania formularza nie potwierdza bieżącego DOM po zalogowaniu.
- Oficjalny OLX API zmienia optymalny kierunek: browser automation należy traktować jako
  działający prototyp i fallback, a nie docelowy pierwszy wybór po uzyskaniu API access.
- Allegro REST API i Allegro Lokalnie to różne zakresy; oficjalna pomoc nadal wyklucza
  wystawianie Lokalnie przez API.
- Docker Desktop uruchomiono i potwierdzono daemon 29.4.0. Systemowy helper
  poświadczeń blokował anonimowy pull; bazowy obraz pobrano z jednorazową pustą
  konfiguracją w `/private/tmp`, bez zmiany zapisanych kont. Następnie build, core doctor
  w kontenerze i trzy testy sieci przeszły: publiczny HTTPS tylko przez proxy, blokada
  localhost oraz blokada bezpośredniego egressu. Kontenery i sieci testowe usunięto.
- Nie instalowano LaunchAgentów w systemie, nie wpisywano tokenów i nie wykonywano
  zewnętrznego skutku.
