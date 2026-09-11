# Stan projektu Marketplace Listing Agent — 2026-09-11

> Dokument wewnętrzny. Opisuje stan zweryfikowany w lokalnym repozytorium. Nie jest
> deklaracją ukończenia funkcji zaplanowanych w `IMPLEMENTATION_PLAN.md`.

## Werdykt

Projekt jest sensownie zaprojektowanym MVP i dobrym punktem wyjścia do nauki AI
Engineering. Ma jawny graf, podział odpowiedzialności, lokalne modele, walidację
Pydantic, SQLite, oddzielne konteksty przeglądarki, podstawowe zabezpieczenia researchu
i mały runner ewaluacyjny.

Nie jest jeszcze gotowy do automatycznego wystawiania ofert na prawdziwym koncie.
Krytyczne, odtworzone błędy kwalifikacji cen i statusu formularza zostały naprawione,
ale zielone testy nadal nie potwierdzają Telegrama, zalogowanych formularzy, restartu
z checkpointem ani publikacji.

Do CV projekt można już wpisać jako aktywnie rozwijany projekt własny, wskazując tylko
elementy faktycznie zaimplementowane. CI, MCP, Docker, automatyczna publikacja,
rozbudowany monitoring i fine-tuning są obecnie planami.

## Aktualizacja wdrożeniowa po audycie bazowym

Po audycie wykonano dwie lokalne iteracje E1/E2. Bieżący zweryfikowany stan ma:

- **54 przechodzące testy**, Ruff bez uwag, poprawną kompilację modułów i 54% pokrycia;
- wspólną bramkę dopuszczenia dowodu do statystyki;
- portalowe ekstraktory publicznych ofert OLX i Allegro Lokalnie oparte na
  zredagowanych fixtures;
- oddzielne rozkłady aktywnych cen ofertowych i cen ofert sprzedanych;
- rekomendacje wyliczane wyłącznie z aktywnych ofert;
- prywatny, atomowo zapisywany manifest dowodów bez HTML, promptów i sekretów;
- dokładne dopasowanie kontrolek formularza oraz readback rozszerzony na kategorię,
  stan, typ sprzedaży, lokalizację i liczbę zdjęć;
- poprawny status `FORM_NEEDS_USER` albo `FAILED`, gdy formularz nie jest gotowy.

Te wyniki są dowodem unit/integration na danych zredagowanych. Nie są dowodem
udanego przebiegu na zalogowanym koncie portalu.

## Identyfikacja kopii

- Repozytorium: `/Users/oliwia/projekty/shopper-bot`.
- Publiczny baseline: `f6c49226e3c7f063ec1b45129be923fdbb4b5ffc`.
- Implementacja powstaje w worktree `/Users/oliwia/Desktop/shopper-bot`, następnie po
  testach jest włączana fast-forward do lokalnego `main`.
- Lokalny `main` zawiera kolejne wdrożenia i jest przed `origin/main`; niczego nie
  wypchnięto do GitHub.

## Co zostało zweryfikowane

### Kod, testy i paczka

| Kontrola | Wynik | Znaczenie |
|---|---:|---|
| `pytest` | 54/54 testy | Testy istniejące przechodzą |
| Pokrycie instrukcji | 54% | Krytyczne integracje nadal wymagają testów przeglądarkowych |
| Ruff | OK | Brak problemów z wybranych reguł lintowania |
| Kompilacja modułów | OK | Kod źródłowy jest składniowo poprawny |
| `uv lock --check` | OK | Lockfile jest spójny z deklaracją zależności |
| Budowa wheel i sdist | OK | Artefakty dają się zbudować |
| Lokalne linki Markdown | OK | Nie znaleziono zerwanych linków do plików |
| `pip-audit` | 0 znanych podatności | Wynik dotyczy obecnie zainstalowanych zależności i bazy audytu z dnia kontroli |
| Bandit | 0 high, 0 medium, 14 low | Głównie szerokie `except`, `assert` i wywołanie macOS `security` |

Największe luki pokrycia po wdrożeniu:

- CLI i runtime: 0%; Telegram: 20%;
- ustawienia aplikacji: 0%;
- runner ewaluacji: 0%;
- formularze: 24%, a sesja przeglądarki: 25%;
- research service: 33%, a źródła: 40%;
- weryfikator stron: około 31%.

Samo zwiększenie procentu nie jest celem. Priorytetem są scenariusze, które mogą
zmienić cenę, użyć błędnej zgody, naruszyć sesję lub doprowadzić do podwójnej publikacji.

### Środowisko lokalne

- macOS 26.3 na Apple Silicon.
- Python 3.12.13 w `.venv`.
- Chrome jest dostępny.
- Ollama działa.
- Dostępne modele:
  - `qwen3.5:4b` — ID `2a654d98e6fb`;
  - `qwen3.5:9b` — ID `6488c96fa5fa`;
  - Bielik 11B v3 Q4_K_M — ID `e8e19ee99d81`;
  - dodatkowo `qwen3.5:27b` — ID `7653528ba5cb`.
- Docker CLI 29.4.0 jest zainstalowany, ale daemon nie działa.
- Token Telegrama i dozwolony `chat_id` nie są skonfigurowane.
- LaunchAgent projektu nie jest zainstalowany.
- `doctor` raportuje braki Telegrama, lecz nadal kończy się kodem 0. Nie nadaje się
  jeszcze na wiarygodny health check w automatyzacji.

### SQLite i dane lokalne

- `data/catalog.sqlite` przechodzi `PRAGMA integrity_check`.
- Tabele `item_cases`, `preferences` i `channel_sessions` są puste.
- `data/checkpoints.sqlite` ma 0 bajtów i nie zawiera schematu.
- W katalogu `data` nie ma zapisanych przedmiotów ani zdjęć.

Nie ma więc lokalnego dowodu, że rzeczywisty przebieg został zatrzymany, zamknięty,
uruchomiony ponownie i wznowiony z checkpointu.

### Repozytorium i dane wrażliwe

- Publiczny zestaw śledzi tylko `data/.gitkeep` i `reports/.gitkeep`, nie lokalne bazy
  ani raporty.
- `.env`, profile Chrome, cache i dane robocze są ignorowane.
- Skan wzorców w plikach i historii śledzonych przez Git nie znalazł rzeczywistego
  klucza, tokenu ani klucza prywatnego. Trafienie dotyczyło pustego pola w
  `.env.example`.
- Lokalny Git zawiera nieosiągalne obiekty. Sprawdzony wzorzec w osieroconym blobie
  okazał się fałszywym alarmem, ale przyszły audyt przed publikacją powinien nadal
  obejmować dokładny indeks i historię referencji.

## Stan według obszarów

### 1. Architektura i graf — częściowo gotowe

Zaimplementowano liniowy LangGraph:

`analyze → review facts → missing info → portals → research → price → draft → audit → review → authorize fill → fill`.

Mocne strony:

- model jest oddzielony od deterministycznych obliczeń ceny;
- inferencja i punkty `interrupt` są zwykle rozdzielone;
- katalog domenowy jest oddzielony od checkpointów;
- zależności grafu są jawnie wstrzykiwane.

Braki:

- brak ścieżek błędów, ponawiania, CAPTCHA i wznowienia pracy formularza;
- brak wersji snapshotu oferty i rejestru operacji zewnętrznych;
- graf zawsze kończy się po wypełnianiu formularzy;
- status końcowy nie wynika z rzeczywistych wyników portali;
- checkpoint nie jest źródłem prawdy dla zgody, ale nie istnieje jeszcze osobny
  trwały rejestr zgód i zadań.

### 2. Telegram i doświadczenie użytkowniczki — prototyp

Zaimplementowano prywatny bot z allowlistą jednego `chat_id`, przyjmowaniem zdjęć,
notatek i komendami `/nowa`, `/gotowe`, `/zaakceptuj`, `/zmien`, `/status`, `/anuluj`.

Braki:

- notatki są trzymane w `context.chat_data`, więc mogą zniknąć po restarcie;
- każde zatwierdzenie używa ogólnego `callback_data="accept"`;
- przycisk nie jest powiązany z przedmiotem, krokiem, wersją, portalem ani jednorazowym
  użyciem;
- bot nie pokazuje pełnego wersjonowanego podglądu przeznaczonego do publikacji;
- nie ma komendy `wystaw`, statusu zadania wykonawcy ani `Kontynuuj` po CAPTCHA;
- nie ma limitów liczby i wielkości zdjęć ani trwałej historii rozmowy;
- format edycji JSON jest mało naturalny dla zwykłego użycia.

### 3. Fakty i modele — działają jako eksperymentalny pipeline

Zaimplementowano role modeli, ustrukturyzowane odpowiedzi, schematy Pydantic, lokalną
inferencję Ollama oraz fallback dla Qwenów. Jeden proces serializuje inferencje.

Znane wyniki baseline:

- fakty: Qwen 4B `2/6`, Qwen 9B `3/6`;
- porównywalność: Qwen 9B `5/5` na małym, poprawionym zbiorze;
- generowanie opisów: Bielik `1/4`;
- audyt opisów: `2/2`;
- plan formularzy: `2/2`;
- matematyka ceny: `3/3`.

To 22 syntetyczne przypadki. Fakty nie są obecnie ewaluowane na prawdziwych zdjęciach,
a metryka głównie sprawdza obecność nazw pól. Bielik dopisywał niepotwierdzone
zapewnienia o funkcjonalności. Audyt i bezpieczny szablon są potrzebne, ale dwa
przypadki audytora nie dowodzą wysokiej skuteczności.

Braki techniczne:

- zwykłe przebiegi nie zapisują pełnej telemetrii modelu;
- raport nie zapisuje commita, hashy datasetu i promptu ani ID/digestu modelu;
- fallback łapie dowolny wyjątek, również potencjalny błąd programistyczny;
- tag modelu nie jest wystarczającym dowodem niezmienności wag;
- brak dostawcy darmowego API i polityki twardo wyłączającej koszty;
- brak monitoringu jakości w czasie.

### 4. Research i wycena — zabezpieczone na poziomie testów lokalnych

Zaimplementowano plan zapytań, profile kategorii, discovery, otwieranie stron,
podstawową ekstrakcję, kontrolę URL/DNS, semantyczny audyt ofert, drugi odczyt wybranych
pozycji i deterministyczne statystyki.

Naprawiono pięć odtworzonych błędów: cenę dostawy, obcą walutę, konflikt DOM/metadata,
kwarantannę `suspicious` i częściowy wynik `unchecked` po timeout. Jedna wspólna bramka
zwraca maszynowe przyczyny odrzucenia i jest używana także dla wyniku częściowego.
Egzekwowany jest minimalny rozmiar próby.

Ekstraktory portalowe ograniczają odczyt do ceny głównego ogłoszenia. Fixtures
odtwarzają rekomendowane oferty, cenę poprzednią i dostawę, aby nie mogły zostać
wybrane przypadkowo. Aktywne i sprzedane oferty mają osobne rozkłady; tylko aktywne
ceny ofertowe tworzą rekomendację. Vinted jest wyłączony.

Pozostają ograniczenia:

- URL po przekierowaniu jest sprawdzany po rozpoczęciu nawigacji;
- kontrola aplikacyjna nie eliminuje DNS rebinding między sprawdzeniem a połączeniem;
- selektory publicznych stron mogą się zmienić i wymagają monitorowania;
- fixtures oraz publiczne strony nie dowodzą działania pełnego researchu na koncie;
- techniczna nazwa `price_pln` wymaga migracji do neutralnego `price_amount`.

### 5. Opisy ofert — zabezpieczony szkic, niewystarczający dowód jakości

Zaimplementowano generator, drugi model audytujący, kilka reguł deterministycznych i
bezpieczny szablon. Cena jest nadpisywana wartością zatwierdzoną przez użytkowniczkę,
a część atrybutów niezgodnych z faktami jest usuwana.

Ryzyka:

- reguły tekstowe nie rozumieją wszystkich polskich parafraz;
- audytor może popełnić ten sam błąd co generator;
- po ręcznej edycji nie jest ponawiany pełny audyt znaczeniowy;
- nowy fakt wpisany w opisie nie staje się jawnie zatwierdzonym faktem;
- brak zamrożonego, reprezentatywnego zbioru niezależnego od promptów.

### 6. Formularze i przeglądarka — bezpieczniejsza beta, bez publikacji

Zaimplementowano oddzielny trwały profil sprzedażowy, bezpieczną serializację zdjęć,
deterministyczne dopasowanie dokładnie jednej kontrolki, ograniczony fallback modelowy,
rozszerzony readback i poprawne agregowanie statusów portali.

Otwarte luki:

- nie ma zredagowanego fixture zalogowanego formularza ani testu pełnego adaptera;
- dostawa, dynamiczne atrybuty i hashe zdjęć nie mają jeszcze pełnego readback;
- szerokie `except Exception` nadal ukrywają część przyczyn awarii;
- nie ma testu CAPTCHA, utraty strony ani zmiany DOM;
- brak automatycznej publikacji, sprawdzenia utworzonej oferty i uzgadniania nieznanego
  wyniku.

### 7. Bezpieczeństwo — dobry kierunek, niepełne egzekwowanie

Istnieją:

- allowlista Telegram `chat_id`;
- token w macOS Keychain;
- oddzielne konteksty research i sprzedaży;
- redakcja pól takich jak serial, IMEI, MEID i UDID;
- kontrola schematu URL, DNS, nietypowych portów i adresów prywatnych;
- ograniczony kontrakt odpowiedzi modeli;
- promptowe oznaczenie treści internetowej jako niezaufanej;
- wykrywanie wybranych niespójności i kwarantanna;
- brak automatycznego kliknięcia publikacji w obecnym kodzie.

Nadal brakuje rzeczywistej izolacji procesowej/sieciowej researchu, ochrony wersji
zgody, limitów plików, polityki retencji, audytowalnego rejestru działań, procedury
incydentu, backupu i testu odtworzenia. Dynamic cloaking jest wykrywany wyłącznie wtedy,
gdy pojawi się obserwowalna różnica. Spójna odpowiedź przygotowana dla automatyzacji
pozostaje niewykrywalna tym mechanizmem.

### 8. Instalacja, CI i eksploatacja — niegotowe

- Wheel i sdist się budują, ale wheel nie zawiera `config/*.yaml` ani goldenów.
- `Settings` wylicza `PROJECT_ROOT` z położenia pliku źródłowego. Po instalacji wheela
  wskazuje nieistniejące ścieżki poza pakietem.
- Program działa obecnie z checkoutu, ale paczka nie jest przenośną instalacją.
- Nie ma `.github/workflows`, Dockerfile ani Compose.
- Nie ma testu czystej instalacji.
- LaunchAgent zakłada konkretną `.venv` wewnątrz checkoutu.
- Brak backupu, migracji, health endpointu i procedury aktualizacji/rollbacku.

### 9. Kurs — wartościowy szkic, wymaga przebudowy

Dziesięć plików przedstawia właściwe pojęcia i dobre decyzje architektoniczne. Materiał
jest jednak krótki i szybko przechodzi od definicji do samodzielnego ćwiczenia.

Brakuje:

- jednego przypadku prowadzonego od zdjęcia do wyniku;
- konkretnych danych wejściowych i stanu po każdym kroku;
- diagramów sekwencji dla sukcesu i awarii;
- szczegółowego SQLite, Git/GitHub Actions, MCP, Dockera, monitoringu i fine-tuningu;
- rozwiązań ćwiczeń i demonstracji błędów;
- synchronizacji ze zmienionym docelowym modelem publikacji;
- jasnego rozdzielenia stanu obecnego i architektury docelowej.

## Funkcje, których nie wolno jeszcze deklarować jako gotowe

- automatyczna publikacja;
- publikacja powiązana z dokładnym podglądem;
- wznowienie CAPTCHA po „już”;
- trwała, naturalna rozmowa po restarcie;
- niezawodna wycena na prawdziwych portalach;
- produkcyjny golden dataset;
- pełny monitoring przebiegu;
- CI w GitHub Actions;
- działający Docker lub MCP;
- dostawca darmowego API;
- LoRA/fine-tuning;
- sprawdzony backup i odtworzenie.

## Najbliższe blokery

1. Naprawić paczkowanie, `doctor` i czystą instalację.
2. Dodać CI i podstawową telemetrię przed rozbudową modeli.
3. Zweryfikować formularze w kontrolowanej sesji zalogowanej i domknąć readback.
4. Wprowadzić wersjonowany snapshot i jednorazową zgodę.
5. Utrwalić rozmowę i przygotować stany interwencji.
6. Dodać izolację researchu, migracje oraz procedurę backupu i odtworzenia.

Szczegółową kolejność, kontrakty i kryteria odbioru opisuje
[`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

## Granice tej weryfikacji

Nie wysłano wiadomości Telegram, nie logowano się do kont sprzedażowych, nie
wypełniano prawdziwych formularzy i nie publikowano ogłoszeń. Nie uruchamiano ponownie
pełnych benchmarków modeli, ponieważ kod, model tags i istniejące raporty baseline nie
uległy zmianie. Nie sprawdzano skuteczności działania na zmienionym DOM portali.

Aktualne zasady portali trzeba ponownie sprawdzić przed wdrożeniem adaptera. Na dzień
audytu oficjalna pomoc Allegro nadal mówi, że API nie publikuje ofert na Allegro
Lokalnie, natomiast dostęp do API OLX wymaga rejestracji i akceptacji aplikacji.
