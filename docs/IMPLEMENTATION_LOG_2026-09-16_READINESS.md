# Domknięcie techniczne przed pierwszym użyciem — 2026-09-16

## Wdrożone

- model nie może sam nadać faktowi źródła `user`; dosłowna wartość musi wystąpić w
  trwałej notatce użytkowniczki;
- zatwierdzony fakt otrzymuje `source_ref`, a snapshot zachowuje pełne rekordy
  pochodzenia obok zgodnego wstecznie słownika wartości;
- formularz wypełnia i odczytuje dostawę oraz dodatkowe atrybuty;
- dopasowanie otwartej strony używa sparsowanego hosta;
- wynik `published` wymaga komunikatu sukcesu i konkretnego URL oferty;
- wyjątek podczas fazy submitu daje `unknown`;
- backup obejmuje bazy SQLite, zdjęcia i konfiguracje oraz weryfikuje SHA-256;
- manifest odróżnia aktualne konfiguracje od własnych modyfikacji, zachowuje te
  modyfikacje podczas kolejnych uruchomień i nie traktuje ich jako awarii;
- MCP przeszedł rzeczywisty handshake klient–serwer po `stdio`;
- checkpoint LangGraph został zamknięty, ponownie otwarty i poprawnie wznowiony;
- research browser wymaga proxy, a Docker wystawia je wyłącznie na loopback;
- CI generuje CycloneDX SBOM jako artefakt.

## Weryfikacja proxy

Zbudowano i uruchomiono `research-proxy`. `doctor --scope research` potwierdził port
`127.0.0.1:18080`. Połączenie przez proxy do `https://example.com` zwróciło HTTP 200,
a próba tunelu do `https://127.0.0.1` została odrzucona HTTP 403.

Proxy ogranicza kierunki sieciowe, lecz research Chrome nadal jest procesem hosta. Nie
jest to pełna izolacja systemu plików i dokumentacja nie przedstawia jej w ten sposób.

## Pozostałe bramki z udziałem użytkowniczki

1. Prywatny Telegram: jeden przedmiot oraz restart przy każdej decyzji.
2. Zalogowany OLX: inventory kontrolek, wypełnienie i readback bez publikacji.
3. Zalogowane Allegro Lokalnie: osobna kontrola formularza bez publikacji.
4. Ręczna ślepa ocena opisów i własne przykłady ze zdjęciami.
5. Opcjonalnie później: jedna dokładnie zatwierdzona publikacja OLX.

Te testy wymagają tokenu, konta lub oceny człowieka. Kod nie może wiarygodnie zastąpić
ich testem syntetycznym.

## Końcowa walidacja techniczna

Wykonana lokalnie 2026-09-16:

- Ruff: bez błędów;
- pytest: **116 testów zakończonych powodzeniem**;
- pokrycie instrukcji: **64%** dla całego pakietu; liczba ta nie jest dowodem
  gotowości portali, dlatego pozostaje uzupełniona testami kontraktów i bramkami live;
- walidacja wszystkich plików JSONL: poprawna;
- skan śledzonych plików pod kątem typowych sekretów: poprawny;
- `uv lock --check`: poprawny;
- paczki wheel i sdist: zbudowane;
- czysta instalacja końcowego wheel poza checkoutem: `doctor --scope core` przeszedł wszystkie
  kontrole, w tym SQLite schema version 5 i manifest ustawień;
- CycloneDX 1.5 SBOM: wygenerowany, 78 komponentów;
- audyt zablokowanych zależności: brak znanych podatności według `pip-audit` w chwili
  testu;
- lokalne odsyłacze Markdown i kontrola whitespace diffu: poprawne.

CI wykonuje ten sam rdzeń kontroli, buduje paczkę, testuje wheel i publikuje SBOM jako
artefakt. Sam plik workflow jest zweryfikowany lokalnie; wykonanie na GitHub Actions
będzie dowodem dopiero po publikacji gałęzi.
