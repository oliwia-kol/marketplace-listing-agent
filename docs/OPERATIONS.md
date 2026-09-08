# Instalacja i eksploatacja

## 1. Środowisko

```bash
uv sync --extra dev
uv run pytest
uv run marketplace-listing-agent doctor
```

Projekt korzysta z zainstalowanego Google Chrome (`channel="chrome"`), więc nie
wymaga osobnej kopii Chromium. Profil sesji sprzedażowej znajduje się w
`data/chrome-profile`. Nie otwieraj równocześnie drugiego procesu z tym samym profilem.

## 2. Modele

```bash
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull hf.co/speakleash/Bielik-11B-v3.0-Instruct-GGUF:Q4_K_M
uv run marketplace-listing-agent doctor
```

Pobieranie jest jednorazowe i zajmuje wiele GB. Model 27B jest opcjonalny:
`ollama pull qwen3.5:27b`. Na testowanym Macu zmieścił się, lecz jego wyładowanie
utknęło, więc konfiguracja używa 9B. Nazwy i role zmieniasz w `config/models.yaml`,
bez zmian w grafie.

## 3. Telegram

1. Utwórz prywatnego bota przez BotFather.
2. Uruchom `uv run marketplace-listing-agent configure-token`; token trafi do macOS Keychain.
3. Wpisz własny liczbowy identyfikator czatu w `.env` jako
   `MARKETPLACE_AGENT_TELEGRAM_ALLOWED_CHAT_ID=...`.
4. Uruchom `uv run marketplace-listing-agent run`.

Przepływ rozmowy: `/nowa` → zdjęcia i opis → `/gotowe` → kolejne akceptacje →
formularze w Chrome → ręczna kontrola i publikacja.

## 4. Ewaluacja i podmiana modelu

```bash
uv run marketplace-listing-agent eval --suite price_math
uv run marketplace-listing-agent eval --suite facts
uv run marketplace-listing-agent eval --suite comparables
uv run marketplace-listing-agent eval --suite copy
uv run marketplace-listing-agent eval --suite forms
uv run marketplace-listing-agent eval --suite copy --model inny-model:tag
```

Raport JSON trafia do `reports/`. Porównuj ten sam commit, ten sam golden dataset i
ten sam sprzęt. Mierz jakość przed szybkością; wynik błędu schematu to niezaliczony
przypadek. `rss_delta_mb` dotyczy procesu Pythona, nie pełnej pamięci Ollama, dlatego
jest wskaźnikiem pomocniczym, a nie miarą VRAM/RAM modelu.

## 5. Start przy logowaniu

Po ukończeniu prób ręcznych uruchom:

```bash
./scripts/install-launch-agent.sh
```

Skrypt tworzy `~/Library/LaunchAgents/pl.marketplace-listing-agent.agent.plist` i ładuje usługę.
To świadoma operacja poza repozytorium, więc nie jest wykonywana automatycznie przez
instalację. Logi lokalne trafią do `data/logs/`.

## 6. Procedura testu adaptera portalu

1. Użyj konta i testowego przedmiotu, którego nie opublikujesz.
2. Zatwierdź tylko jeden portal.
3. Sprawdź każdy odczytany atrybut i screenshot w `data/items/.../evidence`.
4. Potwierdź, że kursor zatrzymuje się przed publikacją.
5. Zanotuj zmianę selektora jako fixture/test przed poprawką kodu.
6. Przed szerokim użyciem sprawdź aktualny regulamin portalu i limity ruchu.

Vinted jest adapterem eksperymentalnym. Ręczne kliknięcie publikacji zmniejsza ryzyko
niezamierzonego działania, ale samo w sobie nie gwarantuje zgodności automatyzacji z
aktualnym regulaminem. W razie wątpliwości wyłącz źródło/adapter w konfiguracji.

## Aktualny wynik smoke testu źródeł

Pierwsze próby z 8 września 2026 poprawnie dotrzymały limitu, ale zwróciły zero
porównań. Diagnostyka znalazła poprawne URL-e OLX i błąd oczekiwania na nieistniejący
tag `meta`; poprawka wymaga ponownego smoke testu. Nie jest to jeszcze walidacja live
scrapera. Przed użyciem do
wyceny wymagany jest niezerowy przebieg oraz ręczne sprawdzenie kilku rekordów;
do tego czasu aplikacja powinna traktować brak rekomendacji jako konieczność wpisania
ceny przez użytkowniczkę, nigdy jako podstawę do automatycznej wyceny.

Kolejna próba potwierdziła 10 dostępnych stron, ale audyt 9B w trybie `think=medium`
przekroczył 300 s. Po przejściu na `think=false` golden audytu uzyskał 2/2, a live
smoke test zamknął się poniżej minuty i zwrócił 2 porównania (35 i 70 zł) z 10
dostępnych stron. Confidence pozostał `low`. Analiza powodów ujawniła zbyt swobodne
wnioskowanie modelu, więc dodano twardą bramkę jawnego dopasowania marki i modelu.
Pełna walidacja nadal wymaga większego, ręcznie oznaczonego zbioru.
