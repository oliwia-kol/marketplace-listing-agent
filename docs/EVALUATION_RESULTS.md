# Wyniki ewaluacji — baseline 2026-09-08

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
Dlatego Bielik pozostaje generatorem szkicu, a nie źródłem prawdy. Każdy szkic
przechodzi audyt 9B i reguły deterministyczne; przy ostrzeżeniu używany jest szablon.

Porównanie faktów wykonano na tym samym rozszerzonym zbiorze i instrukcji. 9B jest
modelem głównym, 4B fallbackiem. Przed utrwaleniem tej decyzji trzeba dodać prawdziwe
zdjęcia, ręczne etykiety i co najmniej 20 przykładów na kategorię.

Raporty JSON w `reports/` zawierają surowe odpowiedzi, czas, tokeny i load time. Są
lokalne i ignorowane przez Git, aby przypadkowo nie opublikować przyszłych danych.
