# Warstwa wiarygodnego opisu — stan wdrożenia 2026-09-14

## Cel

Opis oferty ma być użyteczny sprzedażowo, ale każde twierdzenie ma wynikać z
zatwierdzonego faktu o egzemplarzu albo z oznaczonej, źródłowej specyfikacji modelu.
Model nie ustala ceny, kategorii ani atrybutów formularza. Kod składa te pola z danych
domenowych, a model generuje wyłącznie tytuł i opis.

## Co zostało wdrożone

1. `CopyBrief` dzieli twierdzenia na `item` i `product_spec`. Specyfikacja produktu
   wymaga URL źródła i może zawierać krótki cytat dowodowy. Nie jest automatycznie
   traktowana jako obserwacja stanu sprzedawanego egzemplarza.
2. Copywriter zwraca `CopyTextOutput`, czyli teksty dla wskazanych portali. Cena,
   kategoria, stan i atrybuty formularza są składane deterministycznie.
3. Reguły sprawdzają obecność faktów krytycznych i znane twierdzenia ryzykowne, np.
   niepotwierdzoną sprawność. Osobny model audytuje twierdzenia względem briefu.
4. Przy błędzie jest jedna próba naprawy. Kolejny błąd, zły schemat, brak portalu albo
   przekroczenie wspólnego limitu pięciu minut uruchamia bezpieczny szablon.
5. Ręczna edycja opisu jest ponownie sprawdzana przed utworzeniem snapshotu.
6. SQLite zapisuje brief, draft, audyt, naprawę i finalną wersję po redakcji typowych
   sekretów. Dane wygasają po 30 dniach. `copy-report --run-id ...` tworzy lokalny HTML.
7. `copy-rate` zapisuje pięć ocen człowieka w skali 1–5: naturalność, jasność,
   wiarygodność faktów, dopasowanie do portalu i użyteczność. Ocena jest związana z
   hashem konkretnego wariantu.
8. Runner obsługuje parametry generacji, 1–10 powtórzeń, splity oraz limit przypadków.
   Raport zawiera hashe, model, commit, zagregowane metryki i czasy.

SQLite ma obecnie wersję schematu **5**. Zestawy regresyjne obejmują 120 przypadków
`copy_quality` i 60 parowanych przypadków `copy_audit_mutations`. Są syntetyczne i
oznaczone jako takie; nie zastępują ręcznie etykietowanych ofert.
Obecne splity syntetyczne współdzielą rodziny produktów, więc służą do regresji i prób
runnera. Finalny zbiór realny musi być podzielony po rodzinach produktu bez przecieku.

## Pilot lokalny

Parametry: split `selection`, temperatura 0,2 dla generatorów, seed 42, trzy pierwsze
przypadki Nintendo. To próba techniczna, nie ranking modeli.

| Model | Passed | Recall faktów | Guard | Portale | Średni czas |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B | 0/3 | 0,861 | 0,333 | 1,000 | 17,84 s |
| Bielik 11B v3 Q4 | 2/3 | 0,861 | 0,667 | 1,000 | 18,85 s |

Porażki były materialne: modele dopisywały sprawność, brak innych uszkodzeń albo
stwierdzenie, że wada nie wpływa na działanie. To uzasadnia architekturę
generator → reguły → niezależny audyt → jedna naprawa → fallback → człowiek.

Audytor Qwen3.5 9B uzyskał 6/6 na pierwszych sześciu przypadkach splitu `selection`
(trzy bezpieczne i trzy zmienione), średnio 13,59 s. Wynik nie jest jeszcze miarą
produkcyjną. Pełna próba musi objąć wszystkie rodziny mutacji, powtórzenia i realne
teksty.

## Uzupełnienie: eksperyment na 30 publicznych przypadkach

Po pierwszym wdrożeniu utworzono `copy_real_anonymized.jsonl`: 30 przypadków
znormalizowanych z publicznych ofert OLX i Allegro Lokalnie. Są to twierdzenia
sprzedających, a nie zweryfikowany stan rzeczy. Eksporter usuwa URL i pola
identyfikujące; prywatny manifest źródeł pozostaje poza Gitem.

Pełne porównanie dało Qwen3.5 9B wynik 14/30, a Bielikowi 11B v3 Q4 wynik 3/30.
Zbalansowany screening Qwen3.5 27B dał 5/9 wobec 4/9 Qwen 9B, ale był około 4,4 raza
wolniejszy i miał słabszy guard. Szczegóły i ograniczenia zapisano w
[`EVALUATION_RESULTS_2026-09-14_REAL_COPY.md`](EVALUATION_RESULTS_2026-09-14_REAL_COPY.md).

Runner przyjmuje teraz konkretne `case_ids`, dzięki czemu screening nie zależy od
kolejności rekordów. Dodano też wersjonowane przeliczanie zachowanych odpowiedzi i
generator ślepego pakietu A/B/C z lokalnym zapisem oraz eksportem ocen.

## Co jest nadal otwarte

- Brakuje 30–50 ręcznie sprawdzonych przypadków z własnych zdjęć i notatek. Publiczny
  zbiór 30 ofert jest użytecznym testem realistycznego języka faktów, ale nie dowodem
  prawdziwego stanu przedmiotów.
- Specyfikacje producenta można zapisać, lecz automatyczne pobieranie i weryfikacja
  źródeł producenta nie są jeszcze wdrożone.
- Pakiet ślepego porównania A/B/C jest gotowy, lecz nie ma jeszcze ocen użytkowniczki.
  Pełne 120/60 syntetycznych przypadków nadal służy regresji, a nie decyzji
  produkcyjnej.
- LoRA nie powinna wejść do runtime. Dotychczasowy eksperyment pokonał model bazowy w
  formatowaniu, lecz zremisował z prostym szablonem. Najpierw trzeba wykazać powtarzalny
  błąd semantyczny na realnym zbiorze.
- Formularze zalogowanego OLX i Allegro Lokalnie oraz prawdziwa publikacja pozostają
  osobnymi bramkami operacyjnymi.

## Protokół następnego eksperymentu

1. Zamrozić 20 rodzin produktów jako test, zanim zacznie się strojenie promptu.
2. Porównać co najmniej Bielik 11B, Qwen 9B i Qwen 27B na identycznych briefach.
3. Dla każdego wariantu wykonać trzy powtórzenia z zapisanym seedem i parametrami.
4. Odrzucić wariant, jeśli dopisuje fakt krytyczny, nawet gdy brzmi lepiej.
5. Pozostałe wersje oceniać w ciemno po hashach; raportować średnie ocen człowieka,
   pass rate bezpieczeństwa, recall faktów, p95 czasu i częstość fallbacku.
6. Model wybrać dopiero po całym splicie `selection`; splitu `frozen` użyć raz do
   finalnego potwierdzenia.

## Weryfikacja

- Ruff: passed.
- Pytest z `ResourceWarning`: stan końcowy jest raportowany po pełnej walidacji poniżej.
- JSONL: **180 nowych przypadków**, poprawny format i unikalne identyfikatory w repo.
- Lokalnie dostępne: Qwen3.5 4B/9B/27B i Bielik 11B v3 Q4.
- Wheel i sdist zbudowane; wheel zawiera oba nowe zestawy golden i przeszedł core doctor
  po instalacji do izolowanego katalogu.
- Niczego nie opublikowano i niczego nie wysłano do GitHuba.

## Walidacja końcowa po eksperymencie real-copy

- Ruff: passed.
- Pytest z `ResourceWarning` jako błąd: **100 passed**.
- Wszystkie pliki JSONL: poprawne i z unikalnymi identyfikatorami.
- Wheel i sdist: zbudowane ponownie; wheel zawiera
  `copy_real_anonymized.jsonl` oraz aktualny `models.yaml`.
- Core doctor na świeżym katalogu aplikacji: passed; SQLite schema **5**.
- Blind review: 9 wspólnych przypadków × 3 modele, bez nazw modeli w pakiecie.
- Prywatny manifest URL: potwierdzony jako ignorowany przez Git.
