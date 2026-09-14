# Generalizacja opisów i LoRA v2 — wykonanie 2026-09-14

## Wdrożone

- usunięto automatyczne dokładanie pytań z profilu kategorii;
- pytania pozostają tylko dla sprzeczności lub nierozpoznanego rodzaju przedmiotu;
- fakty bezpośrednio podane przez użytkowniczkę nie wymagają osobnego zatwierdzania;
- odpowiedź na brak może być zwykłym zdaniem;
- copywriter otrzymuje kategorię jako dowód językowy;
- skrócono oczekiwaną długość i zabroniono opisywania typowych funkcji z pamięci;
- zawężono podstawę dla twierdzeń o pełnej sprawności;
- dodano 120 przypadków generalizacji z 12 rodzin;
- blind review pokazuje teraz fakty wejściowe;
- przeprowadzono LoRA v2 rank 8 i rank 16 na 600 przykładach.

## Wyniki screeningu Qwen3.5 9B

Na 12 przykładach AirPods, lokówki, ekspresu i odkurzacza pierwotny pipeline przeszedł
5/12. Po przekazaniu kategorii przeszedł 6/12, a recall faktów wzrósł z 0,944 do 0,979.
Po zmianie promptu ponownie uruchomiono sześć wcześniejszych porażek; pięć przeszło
automatyczne metryki.

Model nadal dopisał typowe funkcje ekspresu, których nie było w briefie. Prosty guard
tego nie wykrył. Wynik uzasadnia pozostawienie audytu semantycznego i finalnego
podglądu. Screening nie jest pełnym wynikiem dla 120 przypadków.

## Wynik LoRA

Oba adaptery nauczyły mały model zwracać prozę, lecz pokrycie dokładnych wartości
spadło do około 0,80. Nazwa przedmiotu była zachowana tylko w połowie frozen testu, a
granica słów po zwrocie otwierającym była poprawna w 53–55% przypadków. Rank 16 nie
dał materialnej poprawy. Adaptery pozostają lokalnym artefaktem eksperymentalnym i nie
zostały podłączone do runtime.

## Otwarte

- pełny przebieg 120 przypadków i trzy seedy;
- ślepa ocena użytkowniczki;
- przykłady z własnymi zdjęciami i zatwierdzonymi opisami;
- kontrolowany test Telegrama po restarcie;
- formularze zalogowanych portali bez publikacji.

## Weryfikacja końcowa

- `ruff check src tests scripts experiments/lora_v2`: bez błędów;
- `pytest -W error::ResourceWarning`: 106 testów zakończonych powodzeniem;
- walidacja wszystkich `goldens/*.jsonl` oraz danych LoRA: bez błędów;
- skan śledzonych i nowych plików pod kątem typowych sekretów: bez znalezisk;
- `git diff --check`: bez błędów białych znaków;
- zbudowany wheel zawiera nowy zbiór `copy_generalization.jsonl`;
- diagnostyka świeżego katalogu aplikacji przeszła ze schematem SQLite w wersji 5.

Weryfikacja potwierdza spójność kodu, paczki i testów automatycznych. Nie stanowi
dowodu działania na zalogowanych kontach OLX i Allegro Lokalnie ani jakości wszystkich
120 odpowiedzi modelu; te dwa zakresy pozostają celowo osobnymi testami ręcznymi.
