# Dziennik wdrożenia planu — 2026-09-11

Ten dokument opisuje faktyczny stan wdrożenia. Po każdym etapie należy aktualizować
status, dowody, otwarte ryzyka i następny krok. Sam wpis w tym pliku nie jest dowodem
działania — dowodem są kod, test i wynik kontrolowanego uruchomienia.

## Środowisko pracy

- baza: commit `f6c49226e3c7f063ec1b45129be923fdbb4b5ffc`;
- gałąź robocza: `codex/implementation-e0-e1`;
- worktree implementacyjny: `/Users/oliwia/Desktop/shopper-bot`;
- wcześniejszy checkout `main`: `/Users/oliwia/projekty/shopper-bot`;
- powód worktree: środowisko tej sesji zezwala na zapis wyłącznie w ścieżce na
  Pulpicie. Worktree chroni `main` i korzysta z tej samej historii Git;
- niczego nie wypchnięto do GitHub i nie opublikowano na portalach.

## Podział prac

| Odcinek | Zakres | Stan |
|---|---|---|
| A1 | E0 oraz krytyczna bramka danych cenowych z E1 | w toku, pierwsza część gotowa |
| A2 | Pozostałe przypadki E1, fixtures portalowe i manifest dowodów | następny |
| A3 | E2: deterministyczne adaptery formularzy i pełny readback | rozpoczęty |
| B1 | E3: paczkowanie, katalog aplikacji i `doctor` | oczekuje |
| B2 | E4: GitHub Actions i kontrole repozytorium | oczekuje |
| C1 | E5: trwała rozmowa, snapshoty i zgody | oczekuje |
| C2 | E6: monitoring, raport przebiegu i golden dataset | oczekuje |
| D1 | E7–E9: worker, CAPTCHA i publikacja OLX | oczekuje |
| D2 | E10–E11: MCP i Allegro Lokalnie | oczekuje |
| E | E12: kontrolowany eksperyment LoRA | oczekuje |

## Wdrożone w odcinku A1/A3

### Research i cena

- dodano jawne `currency` i `price_kind` do kandydata;
- dodano obserwacje ceny z kanału DOM, JSON-LD i metadata;
- rozpoznawane typy: cena przedmiotu, dostawa, rata, poprzednia cena i zakres;
- dodano wykrywanie konfliktu kwoty i waluty między DOM a metadanymi;
- jedna deterministyczna bramka wyklucza rekord:
  - niezweryfikowany;
  - nieporównywalny;
  - `unchecked` albo `suspicious`;
  - w walucie innej niż PLN lub bez potwierdzonej waluty;
  - będący dostawą, ratą, poprzednią ceną albo zakresem;
  - z nieznanym statusem;
- każdy odrzucony kandydat otrzymuje maszynowe `rejection_codes`;
- bramka działa również podczas podsumowania częściowego po timeout;
- `minimum_comparables` jest egzekwowane: obserwacje i mediana pozostają widoczne,
  ale system nie proponuje ceny bez wymaganej próby;
- zwykłe `accept` nie zatwierdzi mediany, jeżeli nie powstała rekomendacja;
- URL-e są kanonizowane przed deduplikacją;
- dopasowanie domeny wymaga dokładnego hosta albo jego subdomeny. `olx.pl.evil.example`
  i `fake-olx.pl` są odrzucane.

### Formularze i status

- poprawiono adres formularza OLX na `https://www.olx.pl/d/nowe-ogloszenie/`;
- Vinted wyłączono w źródłach oraz z listy portali wykonawczych;
- `PortalDraft` zawiera teraz: stan, rodzaj sprzedaży, lokalizację i ustawienia dostawy;
- model copywritera nie może sam wybrać rodzaju sprzedaży, lokalizacji ani dostawy;
- ścieżki zdjęć są zamieniane na bezpieczne DTO przed serializacją promptu;
- AI fallback może wskazać tylko dokładnie jeden element o dokładnej polskiej nazwie;
- substring w rodzaju „Kategoria i opublikuj później” nie przechodzi allowlisty;
- jeżeli formularz zwraca `needs_user`, przedmiot otrzymuje `FORM_NEEDS_USER`;
- `READY_TO_PUBLISH` powstaje tylko wtedy, gdy wszystkie wyniki są `ready`;
- wynik pusty albo `failed` prowadzi do `FAILED`.

## Dowody

Po zmianach:

- `pytest`: **41 passed**;
- Ruff: **all checks passed**;
- compileall: **passed**;
- pokrycie całego pakietu: **50%** (wcześniej 47%);
- pokrycie po zmianach: pricing 94%, extractors 70%, workflow graph 87%;
- testy nie wykonują publikacji ani nie korzystają z zalogowanego profilu.

Nowe regresje obejmują:

1. dostawę `10 zł` przed ceną przedmiotu `1200 zł`;
2. USD w JSON-LD;
3. ratę, poprzednią cenę i zakres;
4. konflikt DOM `1200` kontra metadata `100`;
5. `suspicious` mimo `comparable=True`;
6. `unchecked` po timeout;
7. zbyt małą próbę do rekomendacji;
8. host udający OLX;
9. duplikat URL z parametrami śledzącymi;
10. `Path` zdjęcia w promptcie;
11. formularz wymagający interwencji człowieka.

## Weryfikacja aktualnego interfejsu portali

Sprawdzenie wykonano 11 września 2026 roku przez publiczne strony, oficjalną pomoc
oraz niezalogowaną sesję Playwright. Nie używano hasła, cookies ani prywatnego profilu.

### OLX

Potwierdzone:

- stary adres `/dodaj-ogloszenie/` zwraca 404;
- aktualne wejście `/d/nowe-ogloszenie/` przekierowuje niezalogowaną osobę do
  `login.olx.pl`;
- strona logowania była po polsku i zawierała pola `E-mail`, `Hasło` oraz przycisk
  `Zaloguj się`;
- regulamin wymaga prawdziwego, jasnego opisu oraz umieszczania danych w przeznaczonych
  do tego polach;
- dokładne parametry formularza zależą od kategorii.

Niepotwierdzone bez zalogowania:

- aktualne techniczne selektory pól formularza;
- dokładne nazwy wszystkich pól dla konsol, gier, obiektywów i Apple;
- warianty Przesyłki OLX, rozmiaru paczki, lokalizacji i ewentualnych opłat;
- treść ostatniego przycisku i ekran readback tuż przed publikacją.

Wniosek wykonawczy: adapter OLX ma używać tylko polskich kontraktów pól, ale ich
selektory trzeba utrwalić na kontrolowanym, zalogowanym profilu. Do tego czasu nie wolno
uznać adaptera za gotowy ani implementować publikacji na podstawie domysłów.

### Allegro Lokalnie

Potwierdzone przez aktualną oficjalną instrukcję:

1. formularz zaczyna się od zdjęcia; pojedynczy plik ma limit 25 MB;
2. dalej występują tytuł i wybór kategorii;
3. wymagane są opis oraz stan produktu;
4. użytkownik wybiera `Kup teraz`, `Licytację` albo `Ogłoszenie zwykłe`;
5. formularz wymaga lokalizacji i kończy się podsumowaniem oraz `wystaw jako`;
6. zwykłe ogłoszenie nie ma ustawianej metody dostawy;
7. maksymalna cena wynosi 200 000 zł;
8. oficjalne API nie obsługuje Allegro Lokalnie;
9. wejście `/oferty/wystaw` bez sesji przekierowuje do OAuth Allegro.

Konsekwencje dla modelu danych:

- `sale_type` jest obowiązkową decyzją użytkowniczki dla Allegro Lokalnie;
- ustawienia dostawy zależą od `sale_type`;
- `condition` musi być oddzielnym polem, a nie wyłącznie zdaniem w opisie;
- `location` należy pobrać z lokalnej konfiguracji użytkowniczki lub jawnego wyboru;
- podgląd musi pokazać rodzaj sprzedaży, dostawę i potencjalne koszty;
- przed kliknięciem publikacji automat musi zatrzymać się przy nieoczekiwanej opłacie.

Źródło: [oficjalna instrukcja Allegro Lokalnie](https://allegro.pl/pomoc/dla-kupujacych/sprzedaz-na-allegro-lokalnie/jak-wystawic-ogloszenie-na-allegro-lokalnie-XEB1GldM8HR).

## Decyzje architektoniczne z tej iteracji

1. Nie uczymy modelu tekstów przycisków. Portal ma deterministyczny adapter, a model
   może wyłącznie dopasować brakujące dane do dokładnie widocznej, dozwolonej kontrolki.
2. Obsługujemy polski interfejs. Angielskie alternatywy nie są potrzebne w portalowych
   mapach użytkowych.
3. Cena zachowuje walutę i znaczenie przed dopuszczeniem do statystyki. Nazwa
   `price_pln` w modelu kandydata jest przejściowym długiem technicznym.
4. `suspicious`, `unchecked` i obca waluta pozostają widoczne jako dowód odrzucony,
   zamiast znikać bez śladu.
5. Wybór formy sprzedaży, dostawy i lokalizacji jest decyzją użytkowniczki. Model nie
   może jej wywnioskować z opisu produktu.
6. Status przedmiotu wynika ze wszystkich wyników portali, a nie z samego zakończenia
   funkcji wypełniającej.

## Wątpliwości i ryzyka otwarte

- Ogólne skanowanie tekstu całej strony może znaleźć ceny w rekomendacjach lub reklamach.
  Następny etap musi wprowadzić portalowe fixtures i ograniczone regiony DOM.
- Aktywne ceny ofertowe oraz ceny rzeczywiście sprzedanych przedmiotów są nadal liczone
  razem. Trzeba przygotować osobne statystyki i jasno opisać ich znaczenie.
- Waluta `UNKNOWN` jest bezpiecznie odrzucana, ale zwiększy liczbę brakujących wyników,
  dopóki nie dodamy portalowych ekstraktorów waluty.
- Kontrola URL po przekierowaniu następuje po rozpoczęciu nawigacji. Pełna ochrona przed
  DNS rebindingiem i niebezpiecznymi redirectami wymaga blokowania żądań w kontekście
  researchu.
- Aktualne etykiety pól po zalogowaniu nie zostały potwierdzone. Oficjalny opis procesu
  określa dane, lecz nie stabilny kontrakt DOM.
- Testy są szybkie i deterministyczne, ale nadal nie dowodzą pracy na prawdziwym koncie.

## Następny odcinek A2/A3

1. Dodać portalowe, zredagowane fixtures OLX i Allegro Lokalnie dla strony oferty oraz
   formularza bez przycisku publikacji.
2. Rozdzielić ekstraktory DOM OLX i Allegro Lokalnie od ogólnego fallbacku.
3. Zmienić `price_pln` kandydata na neutralne `price_amount` i dodać migrację raportów.
4. Rozdzielić statystyki ofert aktywnych i sprzedanych.
5. Zapisywać manifest dowodów wraz z kanałami i kodami odrzucenia.
6. Rozszerzyć readback o kategorię, stan, rodzaj sprzedaży, lokalizację, dostawę i zdjęcia.
7. W kontrolowanej sesji zalogowanej jednorazowo zinwentaryzować polskie kontrolki;
   zatrzymać się przed publikacją i nie zapisywać sekretów w repozytorium.
8. Po ustabilizowaniu A2/A3 przejść do paczkowania i GitHub Actions.
