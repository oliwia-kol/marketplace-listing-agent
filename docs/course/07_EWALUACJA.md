# 7. Golden datasets i walidacja modeli

Golden dataset to zestaw wejść z oczekiwanym wynikiem oznaczonym przez człowieka.
Seed w `goldens/` jest syntetyczny i służy do uruchomienia mechanizmu. Dataset
produkcyjny powstaje z realnych, zanonimizowanych przypadków i jasnych instrukcji
anotacji.

Zestawy mierzą inne ryzyka:

- `price_math`: dokładność deterministycznych statystyk;
- `facts`: recall pól i zakazane wymysły;
- `comparables`: accuracy/precision/recall/F1 klasyfikacji;
- `copy`: pokrycie faktów, portali i brak zakazanych twierdzeń;
- `copy_audit`: wykrywanie niepopartych twierdzeń przed akceptacją;
- `forms`: trafność targetów i brak akcji publikacji.

Nie twórz jednej „magicznej oceny”. Fałszywie zaakceptowana oferta porównawcza może
być droższa niż odrzucenie poprawnej, więc patrz szczególnie na precision. Dla faktów
ważny jest hallucination guard. Do czasu i pamięci zawsze dołącz jakość.

Pierwszy baseline i jego uczciwa interpretacja są w `docs/EVALUATION_RESULTS.md`.
Szczególnie ważny jest słaby wynik Bielika w `copy`: naturalność języka nie jest
metryką prawdziwości, dlatego w grafie istnieje osobny audyt i bezpieczny fallback.

## Procedura eksperymentu

1. Zamroź commit i dataset.
2. Uruchom model A trzy razy, potem B trzy razy.
3. Zapisz medianę czasu i rozrzut jakości.
4. Obejrzyj błędy case-by-case.
5. Zmień tylko jedną rzecz: model albo prompt.
6. Dodaj regresyjny golden dla każdego ważnego błędu.

## Ćwiczenie

Oznacz 10 prawdziwych par porównywalna/nieporównywalna. Policz confusion matrix
ręcznie, porównaj z raportem i opisz dwa false positives. To ważniejszy dowód
kompetencji niż sama informacja „użyłam LangGraph”.
