# Stan projektu — 2026-09-14

## Stan wykonawczy

Projekt ma działającą lokalną architekturę MVP oraz warstwę wiarygodnego opisu z
monitoringiem. Najnowszy etap dodał realistyczniejszą ewaluację generatorów, poprawił
błąd guarda i przygotował ślepą ocenę człowieka. Żadna oferta nie została
opublikowana, a GitHub nie został zmieniony.

Późniejszy etap tego samego dnia uprościł rozmowę, dodał 120 przypadków z 12 rodzin i
przeprowadził LoRA v2. Szczegóły znajdują się w
[`IMPLEMENTATION_LOG_2026-09-14_GENERALIZATION.md`](IMPLEMENTATION_LOG_2026-09-14_GENERALIZATION.md).

## Co jest zweryfikowane

- pipeline opisu ogranicza model do tytułu i opisu;
- cena, portal, kategoria i atrybuty formularza pozostają deterministyczne;
- reguły, audyt modelowy, pojedyncza naprawa i szablon zabezpieczają finalny draft;
- SQLite zapisuje wersje, audyty i oceny związane z hashem wariantu;
- 30 zanonimizowanych przypadków publicznych przetestowano na Qwen 9B i Bieliku 11B;
- Qwen 27B przeszedł zbalansowany screening 9 przypadków;
- lokalny pakiet blind review obejmuje dokładnie wspólny podzbiór trzech modeli;
- publiczny golden nie zawiera źródłowych URL, sprzedawców, kontaktów ani cen
  źródłowych; `price_pln=1` jest wyłącznie placeholderem schematu.
- końcowa walidacja: Ruff passed, 100 testów passed, JSONL poprawne, wheel/sdist
  zbudowane, core doctor passed na świeżym katalogu aplikacji.

## Obecna decyzja modelowa

Qwen3.5 9B został ustawiony jako domyślny generator: osiągnął 14/30 wobec 3/30
Bielika. Bielik jest technicznym fallbackiem na wypadek niedostępności modelu, a nie
źródłem prawdy. Qwen3.5 27B nie dał wystarczającego zysku względem około 4,4 raza
większego opóźnienia. Każdy model nadal podlega pełnej bramce bezpieczeństwa.

## Granice dowodu

- publiczne oferty zawierają deklaracje sprzedających, których nie da się potwierdzić;
- ślepy pakiet nie ma jeszcze ocen człowieka;
- zalogowane formularze OLX i Allegro Lokalnie nie przeszły kontrolowanego testu;
- CI jest skonfigurowane, ale bieżąca gałąź nie została wysłana na GitHub;
- LoRA pozostaje eksperymentem i nie jest częścią runtime.
- LoRA v2 rank 8 i 16 rzeczywiście wytrenowano; oba odrzucono po frozen teście z
  powodu utraty części nazw i wartości faktów.

## Kolejne bramki

1. Wypełnić blind review przed otwarciem klucza modeli.
2. Uruchomić 30 przypadków przez pełny pipeline i policzyć częstość naprawy/fallbacku.
3. Dodać własne przypadki ze zdjęciami oraz faktami zatwierdzonymi przez użytkowniczkę.
4. Przeprowadzić test formularzy w izolowanym profilu, bez kliknięcia publikacji.
5. Dopiero potem zamrozić model, prompt i golden do wersji portfolio.
