# Dziennik wdrożenia planu — 2026-09-11

Ten dokument opisuje faktyczny stan wdrożenia. Po każdym etapie należy aktualizować
status, dowody, otwarte ryzyka i następny krok. Sam wpis w tym pliku nie jest dowodem
działania — dowodem są kod, test i wynik kontrolowanego uruchomienia.

## Środowisko pracy

- baza: commit `f6c49226e3c7f063ec1b45129be923fdbb4b5ffc`;
- bieżąca gałąź robocza: `codex/implementation-a2`;
- worktree implementacyjny: `/Users/oliwia/Desktop/shopper-bot`;
- wcześniejszy checkout `main`: `/Users/oliwia/projekty/shopper-bot`;
- powód worktree: środowisko tej sesji zezwala na zapis wyłącznie w ścieżce na
  Pulpicie. Worktree chroni `main` i korzysta z tej samej historii Git;
- po pozytywnej weryfikacji pierwszy commit został lokalnie włączony do `main`
  operacją fast-forward; zdalny GitHub nie został zmieniony;
- niczego nie wypchnięto do GitHub i nie opublikowano na portalach.

## Podział prac

| Odcinek | Zakres | Stan |
|---|---|---|
| A1 | E0 oraz krytyczna bramka danych cenowych z E1 | pierwsza iteracja zakończona |
| A2 | Pozostałe przypadki E1, fixtures portalowe i manifest dowodów | zakończony w zakresie publicznych stron ofert |
| A3 | E2: deterministyczne adaptery formularzy i pełny readback | częściowo wdrożony; wymaga kontrolowanej sesji zalogowanej |
| B1 | E3: paczkowanie, katalog aplikacji i `doctor` | oczekuje |
| B2 | E4: GitHub Actions i kontrole repozytorium | oczekuje |
| C1 | E5: trwała rozmowa, snapshoty i zgody | oczekuje |
| C2 | E6: monitoring, raport przebiegu i golden dataset | oczekuje |
| D1 | E7–E9: worker, CAPTCHA i publikacja OLX | oczekuje |
| D2 | E10–E11: MCP i Allegro Lokalnie | oczekuje |
| E | E12: kontrolowany eksperyment LoRA | oczekuje |

## Wdrożone w odcinku A1–A3

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
- dodano osobne parsery publicznych ofert OLX i Allegro Lokalnie;
- parser OLX odczytuje cenę wyłącznie z głównego kontenera
  `data-testid="ad-price-container"`;
- parser Allegro Lokalnie odczytuje bieżącą cenę z głównej metadanej
  `itemprop="price"`, zachowując cenę poprzednią jako osobny typ;
- rekomendowane oferty i dostawa nie są skanowane jako cena głównego przedmiotu;
- zredagowane fixtures odwzorowują jedynie elementy potrzebne do testu, bez danych
  konta i kopii całych stron;
- statystyki ofert aktywnych i sprzedanych są rozdzielone;
- rekomendacje oraz poziom pewności wynikają wyłącznie z aktywnych cen ofertowych;
- każdy research zapisuje atomowo prywatny manifest JSON z kandydatami, kanałami
  dowodu, wynikami bramki i przyczynami odrzucenia. Manifest nie zawiera HTML, promptów,
  cookies ani sekretów i ma uprawnienia pliku `0600`.

### Formularze i status

- poprawiono adres formularza OLX na `https://www.olx.pl/d/nowe-ogloszenie/`;
- Vinted wyłączono w źródłach oraz z listy portali wykonawczych;
- `PortalDraft` zawiera teraz: stan, rodzaj sprzedaży, lokalizację i ustawienia dostawy;
- model copywritera nie może sam wybrać rodzaju sprzedaży, lokalizacji ani dostawy;
- ścieżki zdjęć są zamieniane na bezpieczne DTO przed serializacją promptu;
- AI fallback może wskazać tylko dokładnie jeden element o dokładnej polskiej nazwie;
- deterministyczne wyszukiwanie kontrolek także wymaga dokładnej etykiety lub
  placeholdera oraz dokładnie jednego dopasowania;
- natywne `input`, `textarea` i `select` są obsługiwane zgodnie z typem kontrolki;
- readback obejmuje tytuł, opis, cenę, kategorię, stan, rodzaj sprzedaży, lokalizację
  oraz liczbę zdjęć, o ile pole zostało rzeczywiście wypełnione;
- substring w rodzaju „Kategoria i opublikuj później” nie przechodzi allowlisty;
- jeżeli formularz zwraca `needs_user`, przedmiot otrzymuje `FORM_NEEDS_USER`;
- `READY_TO_PUBLISH` powstaje tylko wtedy, gdy wszystkie wyniki są `ready`;
- wynik pusty albo `failed` prowadzi do `FAILED`.

## Dowody

Po drugiej iteracji:

- `pytest`: **54 passed**;
- Ruff: **all checks passed**;
- compileall: **passed**;
- pokrycie całego pakietu: **54%** (baseline 47%);
- pokrycie kluczowych modułów: pricing 97%, portal extractors 89%, evidence 100%,
  workflow graph 87%;
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
12. cenę rekomendowanej oferty i dostawy na fixture OLX;
13. starą cenę, dostawę i polecane oferty na fixture Allegro Lokalnie;
14. aktywne ceny ofertowe kontra jawnie sprzedane;
15. brak rekomendacji, gdy istnieją wyłącznie ceny sprzedanych ofert;
16. zapis manifestu, bezpieczne `item_id` i uprawnienia pliku;
17. przekazanie `item_id` z grafu do researchu;
18. rozszerzony kontrakt readback i komunikat Telegrama rozdzielający rodzaje danych.

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

## Wątpliwości i ryzyka otwarte po drugiej iteracji

- Portalowe parsery opierają się na selektorach potwierdzonych 11 września 2026 roku.
  Zmiana DOM bez wersjonowanego monitoringu selektorów może zmniejszyć liczbę wyników;
  bezpieczne zachowanie to brak ceny, a nie skanowanie przypadkowych kwot.
- Waluta `UNKNOWN` jest bezpiecznie odrzucana, ale zwiększy liczbę brakujących wyników,
  dopóki nie dodamy portalowych ekstraktorów waluty.
- Kontrola URL po przekierowaniu następuje po rozpoczęciu nawigacji. Pełna ochrona przed
  DNS rebindingiem i niebezpiecznymi redirectami wymaga blokowania żądań w kontekście
  researchu.
- Aktualne etykiety pól po zalogowaniu nie zostały potwierdzone. Rozszerzony readback
  ma kontrakt i logikę typów, lecz nie jest jeszcze dowodem działania na prawdziwym
  formularzu. Dostawa oraz hashe zdjęć wymagają portalu i kontrolowanej sesji.
- Szerokie przechwytywanie wyjątków w formularzach nadal utrudnia diagnostykę; kolejny
  etap ma dodać typowane błędy oraz zdarzenia bez danych wrażliwych.
- Pole `price_pln` kandydata pozostaje mylące dla kwoty w obcej walucie. Zmiana nazwy
  wymaga jawnej migracji zapisanych raportów i checkpointów, więc zostaje połączona
  z etapem migracji danych zamiast wykonywania niekompatybilnej zmiany w locie.
- Testy są szybkie i deterministyczne, ale nadal nie dowodzą pracy na prawdziwym koncie.

## Następny odcinek B1/B2 oraz domknięcie A3

1. Naprawić paczkowanie zasobów YAML i ścieżki po instalacji wheel.
2. Zbudować wiarygodny `doctor` z niezerowym kodem dla braków wymaganych przez wybrany
   tryb pracy.
3. Dodać czystą instalację i test uruchomienia CLI.
4. Dodać GitHub Actions dla testów, Ruff, budowy paczki i kontroli sekretów.
5. Zastąpić szerokie wyjątki formularza typowanymi zdarzeniami diagnostycznymi.
6. W kontrolowanej sesji zalogowanej jednorazowo zinwentaryzować polskie kontrolki;
   zatrzymać się przed publikacją i nie zapisywać sekretów w repozytorium.
7. Na podstawie tej inwentaryzacji dodać zredagowane fixtures formularzy, dostawę,
   hashe zdjęć i test kompletnego readback.
8. Zmianę `price_pln` na neutralne `price_amount` wykonać razem z migracją schematu
   raportów i checkpointów.
