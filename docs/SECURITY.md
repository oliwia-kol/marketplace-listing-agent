# Cybersecurity i integralność dowodów

## Model zagrożeń

System ma cztery granice zaufania: Telegram, publiczny internet, lokalne modele i
zalogowany profil Chrome. Chronione zasoby to konta sprzedażowe, token bota, zdjęcia,
dane urządzeń, zatwierdzone fakty, historia decyzji i wiarygodność wyceny.

Najważniejsze scenariusze:

1. złośliwy link prowadzi do `localhost`, routera lub usługi w sieci lokalnej (SSRF);
2. tytuł oferty zawiera prompt injection nakazujący modelowi zmienić reguły;
3. strona pokazuje automatowi inną cenę/treść niż zwykłemu użytkownikowi (cloaking);
4. cena w metadanych różni się od ceny użytej przez stronę;
5. model wymyśla cechę, a formularz lub opis ją publikuje;
6. zmiana DOM kieruje kliknięcie na przycisk publikacji;
7. numer seryjny, IMEI, token albo ścieżka zdjęcia trafia do logu lub wyszukiwarki;
8. zależność, model albo plik konfiguracyjny zostaje podmieniony.

## Zaimplementowane kontrole

| Ryzyko | Kontrola | Zachowanie przy błędzie |
|---|---|---|
| SSRF | tylko HTTP(S), port 80/443, bez credentials, kontrola literalnego IP i DNS | URL odrzucony przed Playwright |
| redirect do sieci lokalnej | ponowna kontrola finalnego URL i DNS | wynik odrzucony |
| prompt injection | model dostaje wyłącznie ograniczone pola; prompt oznacza treść jako niezaufaną; model nie ma narzędzi | treść nie może zmienić grafu ani uruchomić akcji |
| sprzeczne metadane ceny | porównanie `meta` i JSON-LD | kandydat trafia do kwarantanny |
| dynamiczna zmiana | ponowne otwarcie zaakceptowanego kandydata i porównanie URL, ceny, tytułu i statusu | kandydat trafia do kwarantanny |
| błędna tożsamość | deterministyczna bramka marki/modelu + profil kategorii + audyt 9B | brak udziału w statystyce |
| halucynacja opisu | Pydantic, audyt 9B, deterministyczny guard, bezpieczny szablon i HITL | szkic zastąpiony/oczekuje na decyzję |
| niechciana publikacja | allowlista akcji i słów, osobny interrupt, ręczne kliknięcie publikacji | automat nie publikuje |
| przejęcie Telegrama | jeden dozwolony `chat_id`, token w Keychain | obcy czat odrzucony |
| wyciek identyfikatorów | klucze `identifier`, `serial`, `imei`, `meid`, `udid` usuwane przed planem wyszukiwania | sekret nie może wejść do query |
| niekontrolowana autonomia | jawny graf i brak swobodnego tool-callingu z tekstu strony | tylko zaprogramowany następny krok |

Kwarantanna jest widoczna w podsumowaniu ceny. Kandydat oznaczony jako `suspicious`
nie może być `comparable`, więc nie zmienia mediany ani rekomendacji.

## Dynamic cloaking — granica obecnej detekcji

Cloaking to selektywne serwowanie innej treści zależnie np. od nagłówków, fingerprintu
przeglądarki, JavaScriptu, cookies, adresu IP, czasu lub wykrycia automatyzacji. Może
być celowe, ale podobny objaw daje legalny eksperyment A/B, personalizacja, zmiana
ceny albo wygasająca oferta. System wykrywa **niespójność**, nie przypisuje intencji.

Obecna warstwa wykrywa różnice między kanałami strukturalnymi strony i dwoma
odczytami w zwykłym Playwright. Nie wykryje cloakingu, który konsekwentnie oszukuje
każdy odczyt tej samej automatyzacji. To istotne ograniczenie, a nie „rozwiązany”
problem. Badania measurement pokazują, że bot detection może zmieniać obserwowaną
treść i zniekształcać wyniki: [Detecting Bot Detection](https://arxiv.org/abs/2606.14525).

## Zaplanowane wzmocnienia

- kontrolna próbka otwierana ręcznie w zwykłym profilu Chrome i porównywana z dowodem;
- porównanie DOM widocznego, JSON-LD i odpowiedzi sieciowej z tolerancją per portal;
- podpisany rekord dowodowy: timestamp, domena, hash tytułu/ceny/statusu i wersja ekstraktora;
- testy kanarkowe znanych ofert oraz alarm nagłej zmiany rozkładu odrzuceń;
- reguły anomalii: duplikaty, skupiska identycznych cen, skrajne outliery i jedna domena;
- pinowanie lockfile, skan zależności, SBOM i przegląd aktualizacji;
- szyfrowanie lokalnych danych oraz polityka retencji zdjęć/checkpointów;
- testy prompt injection z benchmarkiem niezaufanej treści webowej;
- manualny security review przed połączeniem prawdziwych kont sprzedażowych.

Nie planujemy stealth pluginów, rotacji proxy, obchodzenia CAPTCHA ani omijania
zabezpieczeń portali. Celem jest wykrycie niewiarygodnego pomiaru i zatrzymanie
procesu, nie ukrywanie automatyzacji.

## Reagowanie

Przy nietypowym wzroście kwarantanny: nie publikować rekomendacji, zachować jedynie
zanonimizowany raport diagnostyczny, sprawdzić ręcznie 2–3 strony, odświeżyć adapter
i dopiero potem ponowić badanie. Token ujawniony w logach należy unieważnić, zmienić
w Keychain i sprawdzić historię czatu. Podejrzanej strony nie otwieramy w profilu
sprzedażowym — research i sprzedaż mają oddzielne konteksty.
