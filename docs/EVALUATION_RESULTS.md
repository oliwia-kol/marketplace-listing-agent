# Wyniki ewaluacji

Aktualny wybór generatora na 30 zanonimizowanych przypadkach publicznych znajduje się
w [`EVALUATION_RESULTS_2026-09-14_REAL_COPY.md`](EVALUATION_RESULTS_2026-09-14_REAL_COPY.md).
Pełny raport z 120 przypadków syntetycznych oraz eksperymentu LoRA znajduje się w
[`EVALUATION_RESULTS_2026-09-13.md`](EVALUATION_RESULTS_2026-09-13.md). Poniższy zapis
jest historycznym baseline'em z 08.09 i pokazuje, dlaczego dodano guardy oraz szersze
zestawy testowe.

## Baseline 2026-09-08

Datasety są syntetycznymi seed goldenami. Wyniki pokazują zachowanie konkretnej
wersji promptów i modeli lokalnych; nie są deklaracją jakości produkcyjnej.

| Zestaw | Model/warstwa | Wynik | Wniosek |
|---|---|---:|---|
| `price_math` | kod deterministyczny | 3/3 | statystyka działa na znanych przykładach |
| `forms` | Qwen 4B + safety policy | 2/2 | plan nie zawiera niedozwolonych kliknięć |
| `comparables` | Qwen 9B | 5/5 | rozróżnia warianty Fuji/Switch i prompt injection na małej próbce |
| `copy_audit` | Qwen 9B | 2/2 | wykrył niepoparte cechy i zaakceptował bezpieczny szablon |
| `facts` | Qwen 4B | 2/6 | zbyt niestabilny jako model główny |
| `facts` | Qwen 9B | 3/6 | lepszy od 4B, ale nadal wymaga HITL i większego datasetu |
| `copy` | Bielik 11B v3 | 1/4 | naturalny tekst nie gwarantuje wierności faktom |

Przy `copy` część porażek wynika z literalnej metryki fraz i polskiej fleksji, ale
dwa błędy są merytoryczne: model dopisał „nie wpływa na funkcjonalność/jakość”.
Dlatego żaden model nie jest źródłem prawdy. Od 14.09 Qwen3.5 9B jest domyślnym
generatorem, a Bielik technicznym fallbackiem. Każdy szkic przechodzi audyt 9B i
reguły deterministyczne; przy ostrzeżeniu używany jest szablon.

Porównanie faktów wykonano na tym samym rozszerzonym zbiorze i instrukcji. 9B jest
modelem głównym, 4B fallbackiem. Przed utrwaleniem tej decyzji trzeba dodać prawdziwe
zdjęcia, ręczne etykiety i co najmniej 20 przykładów na kategorię.

Raporty JSON w `reports/` zawierają surowe odpowiedzi, czas, tokeny i load time. Są
lokalne i ignorowane przez Git, aby przypadkowo nie opublikować przyszłych danych.

## LoRA 2026-09-13

Wykonano rzeczywisty trening MLX-LM `Qwen/Qwen3-0.6B`: 240 przykładów train, 30
validation i 30 zamrożonych testów, rozdzielonych po rodzinie produktu. Adapter uczył
1,442 mln parametrów (0,242%), osiągnął szczyt 1,797 GB pamięci i ma 5,78 MB.

Na syntetycznym teście model bazowy powtarzał JSON (`prose_format=0,0`), a LoRA
zwróciła oczekiwany opis w 30/30 przypadków. Deterministyczny szablon uzyskał taki sam
wynik, dlatego adapter nie wszedł do domyślnej konfiguracji. Pełne metryki, hashe,
ograniczenia i decyzja znajdują się w
[`../experiments/lora/RESULTS.md`](../experiments/lora/RESULTS.md).
