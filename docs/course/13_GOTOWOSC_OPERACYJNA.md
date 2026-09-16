# Lekcja 13: kiedy prototyp jest gotowy do użycia

## 1. Problem

Zielone testy mówią, że sprawdzone zachowania działają. Nie mówią, że aktualny portal,
konto, sesja Chrome i cały proces zachowają się identycznie. Gotowość wymaga połączenia
poprawności kodu, odporności na awarie i kontrolowanego testu środowiska.

## 2. Pochodzenie faktu

Model może zwrócić `source="user"`, ale samo pole JSON nie tworzy zaufania. Program
porównuje wartość z trwałą notatką. Dosłownie obecna wartość dostaje hash notatki jako
`source_ref`; parafraza pozostaje propozycją modelu i wymaga zatwierdzenia.

```text
wiadomość → ekstrakcja → kontrola pochodzenia → akceptacja → fact_records → snapshot
```

Snapshot przechowuje prosty słownik potrzebny aplikacji i pełne rekordy pochodzenia.

## 3. Readback jako kontrola skutku

Wypełnienie pola nie dowodzi, że portal zachował wartość. Program odczytuje ponownie
tytuł, opis, cenę, kategorię, stan, typ sprzedaży, lokalizację, dostawę, atrybuty i liczbę
zdjęć. Różnica zatrzymuje zadanie i wymaga nowego podglądu.

## 4. Dlaczego `unknown` jest poprawnym stanem

Po kliknięciu publikacji połączenie może zniknąć. Ponowne kliknięcie grozi duplikatem.
Dlatego wyjątek w fazie `submitting` daje `unknown`. Reconciliation obserwuje portal i
szuka konkretnego URL oferty; nie ponawia publikacji.

```text
authorized → submitting → published
                       ↘ unknown → reconciliation
```

## 5. Backup a prawdziwe odtworzenie

Sama baza nie wystarcza, ponieważ snapshot odwołuje się do zdjęć. Backup zapisuje obie
bazy, zdjęcia i konfiguracje oraz hash każdego pliku. Restore sprawdza integralność i
odmawia nadpisania niepustego katalogu. Spójną kopię wydania wykonuje się przy zatrzymanym
orchestratorze i workerze.

## 6. Granica proxy

Research Chrome działa na Macu, ale jego ruch przechodzi przez Docker CONNECT proxy.
Proxy odrzuca prywatne i specjalne adresy oraz przypina sprawdzony adres DNS. Chroni to
przed SSRF i rebindingiem na poziomie egressu. Nie chroni plików hosta przed samym
procesem Chrome, więc nie nazywamy tego pełnym sandboxem.

## 7. Test przed pierwszym użyciem

1. Uruchom proxy i wszystkie zakresy `doctor`.
2. Utwórz nieistotny przedmiot w prywatnym Telegramie.
3. Zatrzymaj proces na decyzji, uruchom ponownie i dokończ krok.
4. Powtórz dla ceny, opisu i podglądu.
5. Wypełnij OLX bez publikacji i porównaj wszystkie pola.
6. Wywołaj kontrolowaną różnicę i sprawdź `waiting_user`.
7. Wykonaj backup, restore do pustego katalogu i core doctor.

## 8. Odpowiedź rekrutacyjna

„Oddzieliłam testy kodu od dowodu działania integracji. Fakt modelowy nie uzyskuje
autorytetu przez własną deklarację. Przed operacją zewnętrzną używam niezmiennego
snapshotu i readbacku, a niepewny submit przechodzi do reconciliation bez retry. Backup
obejmuje również pliki, od których zależą hashe snapshotu. Egress researchu jest
ograniczony proxy, ale jawnie opisuję, że nie jest to pełny sandbox procesu.”
