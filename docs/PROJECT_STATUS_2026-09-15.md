# Stan projektu i plan domknięcia — 2026-09-15

## Wniosek wykonawczy

Projekt jest rozbudowanym, lokalnym prototypem AI z trwałym workflow, ewaluacją,
zabezpieczeniami, MCP, Dockerem i eksperymentami LoRA. Warstwy domenowe są rzeczywiście
zaimplementowane i testowane. Nie jest jeszcze uczciwie nazywać go zweryfikowanym
produktem portalowym: zalogowane formularze OLX i Allegro Lokalnie, restart prawdziwej
rozmowy Telegram oraz publikacja nie przeszły kontrolowanego testu użytkowego.

Najważniejszym kolejnym krokiem jest test całego przepływu na jednym rzeczywistym
przedmiocie bez publikacji. Dalsze strojenie modeli przed tym testem ma mniejszą wartość.

## Zweryfikowany stan repozytorium

Punkt audytu przed aktualizacją dokumentów: commit `0d0dffb`, gałąź
`codex/implementation-a2`. Repozytorium zawierało 194 śledzone pliki, 49 modułów Python
w `src` i 27 plików testowych.

- Ruff: bez błędów dla całego repozytorium;
- pytest: **106 testów przeszło** z `ResourceWarning` traktowanym jak błąd;
- pokrycie instrukcji `marketplace_agent`: **63%**;
- JSONL: poprawna struktura i unikalne identyfikatory;
- skan typowych sekretów: bez znalezisk w bieżących plikach i osiągalnej historii Git;
- lockfile: spójny;
- wheel i sdist: zbudowane;
- wheel zainstalowany w pustym Pythonie 3.12; `doctor --scope core` przeszedł;
- SQLite: integralny, schemat w wersji **5**;
- `docker compose config --quiet`: przeszedł;
- audyt zależności `pip-audit --disable-pip`: brak znanych podatności w lockfile;
  zwykły tryb tworzący pomocniczy virtualenv nie działał lokalnie, dlatego wynik ma
  zostać niezależnie powtórzony przez Linux runner w CI.

63% nie oznacza równomiernego bezpieczeństwa. Domena, ceny i copy mają przeważnie
89–98%, natomiast Telegram ma 19%, formularze 23%, sesja przeglądarki 25%, wykonawca
42%, a serwer MCP 36%. To wskazuje, gdzie potrzebne są testy integracyjne.

## Plan E0–E12 kontra wykonanie

| Etap | Stan | Dowód | Co pozostało |
|---|---|---|---|
| E0 baseline | wykonany | manifest, konfiguracje, rozdzielenie danych aplikacji, statusy dowodu | ustalić jedną codzienną kopię roboczą po scaleniu |
| E1 research i cena | wykonany na fixtures | wspólna bramka ceny, DOM/JSON-LD/meta, SSRF, deduplikacja, testy portalowe | kontrolna próbka z aktualnych stron i analiza driftu |
| E2 formularze bez publikacji | częściowy | DTO, allowlista akcji, readback, agregacja wyników, testy atrap | zalogowany OLX i Allegro Lokalnie bez submitu |
| E3 paczka i diagnostyka | wykonany | wheel, pusta instalacja, app directory, doctor, LaunchAgents | test LaunchAgentów po restarcie komputera |
| E4 GitHub Actions | skonfigurowany | workflow i Dependabot w repo | zdalny zielony run i test, że błąd blokuje PR |
| E5 kontekst i zgody | zaimplementowany lokalnie | SQLite v5, checkpointy, snapshoty, hashe zdjęć, jednorazowe zgody | rzeczywisty restart na każdym ważnym `interrupt` |
| E6 monitoring i evals | częściowy | RunEvent, raport HTML, hashe, goldeny, copy ratings | oceny człowieka, pełne 120 × 3 seedy, raport fallbacków; eksport LangSmith jest opcjonalny |
| E7 worker i interwencje | częściowy | osobny worker, lease, CAPTCHA/login/fee states, resume, emergency stop | test na trwałym profilu Chrome i prawdziwej CAPTCHA/login expiry |
| E8 Docker | wykonany lokalnie | non-root/read-only, osobny egress proxy, wcześniejsze testy pozytywne i negatywne | cykliczna kontrola obrazu i SBOM |
| E9 OLX publish/reconcile | prototyp | druga zgoda, readback, exact button, `unknown`, reconciliation | aktualny formularz, opłaty, pojedynczy osobno zatwierdzony test rzeczywisty |
| E10 MCP | częściowy | lokalny stdio, wąskie narzędzia po ID, wspólna autoryzacja, testy facade | test protokołu z rzeczywistym klientem MCP i dopiero potem demonstracja wykonawcza |
| E11 Allegro Lokalnie | prototyp | osobny spec adaptera, fixture i ekstraktor | kontrolowany zalogowany formularz; brak wspieranego publish API trzeba okresowo weryfikować |
| E12 LoRA | wykonany jako eksperyment | dwa treningi, frozen test, hashe danych i adapterów | nie integrować; wrócić dopiero z ręcznie sprawdzonym korpusem i nową hipotezą |

## Warstwa opisu

Generator Qwen3.5 9B pozostaje domyślnym copywriterem, ale nie jest źródłem prawdy.
Pipeline przekazuje zatwierdzone fakty, sprawdza twierdzenia regułami i osobnym audytem,
wykonuje najwyżej jedną naprawę, a potem przechodzi do bezpiecznego szablonu. Człowiek
widzi i zatwierdza finalny tekst.

Zbiór generalizacji ma 120 przypadków z 12 rodzin. Screening wykrył i naprawił brak
kategorii w briefie, lecz pokazał także halucynowanie typowych funkcji ekspresu. Pełny
benchmark 120 przypadków i trzy seedy nie został wykonany.

LoRA v2 na Qwen3-0.6B nauczyła prozy, ale pogorszyła zachowanie dokładnych faktów do
około 0,81 i zachowywała nazwę przedmiotu tylko w połowie zamrożonych przypadków.
Adaptery słusznie pozostają poza runtime.

## Bezpieczeństwo

Zaimplementowane są: źródła i akceptacje faktów, niezmienne snapshoty, zgody związane z
wersją, blokada powtórzeń, fail-closed pricing, SSRF/DNS controls, odseparowany profil
sprzedażowy, wąski kontrakt MCP, blokada live submit domyślnie, CAPTCHA jako interwencja,
redakcja telemetryczna oraz izolowany egress researchu.

Otwarte pozostają dowody operacyjne: przegląd threat modelu na aktualnym formularzu,
retencja zdjęć i checkpointów w realnym użyciu, szyfrowanie danych w spoczynku, SBOM,
test odtworzenia prawdziwego backupu, test kradzieży/blokady profilu oraz procedura
reakcji na zmianę regulaminu i DOM portalu.

## Kurs i gotowość do rozmowy

Podręcznik obejmuje cały program modułów 0–19: architekturę, Python, LangGraph, SQLite,
modele, bezpieczeństwo, browser automation, monitoring, Git/CI, Docker, MCP i LoRA.
Osobne prowadzone lekcje istnieją dla tematów 1–12. Brakuje praktycznych, wykonanych
laboratoriów dla GitHub Actions, protokołu MCP, odzyskiwania po awarii i pełnego demo.

Do CV można już bronić: projekt architektury, lokalny workflow, persistence, pricing,
evals, zabezpieczenia, paczkowanie, Docker, MCP jako lokalny interfejs oraz wykonany i
odrzucony eksperyment LoRA. Nie należy jeszcze deklarować produkcyjnego wdrożenia,
zweryfikowanej integracji z kontem ani rzeczywistej publikacji.

## Kolejność dalszych prac

1. Doprowadzić PR do zielonego CI i scalić zweryfikowany stan.
2. Uruchomić prywatny Telegram na jednym testowym przedmiocie; sprawdzić restart przy
   faktach, cenie, opisie i podglądzie.
3. W odseparowanym profilu Chrome zinwentaryzować aktualne polskie formularze OLX i
   Allegro Lokalnie, wypełnić je i wykonać readback bez publikacji.
4. Dodać testy integracyjne Telegrama, formularzy, workera i MCP na podstawie znalezionych
   awarii; celem jest pokrycie krytycznych ścieżek, a nie arbitralny procent.
5. Przygotować 30–50 własnych, ręcznie zatwierdzonych przypadków oraz wypełnić blind
   review. Następnie uruchomić 120 przypadków × 3 seedy i policzyć fallback/repair rate.
6. Wykonać threat-model review, SBOM, test backup/restore oraz politykę retencji.
7. Nagrać lub zapisać redacted end-to-end demo i cztery laboratoria kursowe.
8. Dopiero po powyższych bramkach rozważyć jedną rzeczywistą publikację OLX, z osobną
   zgodą na dokładny snapshot. Allegro Lokalnie może pozostać późniejszym etapem.

Nowa LoRA, większy model i LangSmith nie są obecnie priorytetem. Największą wartość dla
produktu i CV da teraz dowód pełnego przepływu, ręczna ocena jakości i recovery.
