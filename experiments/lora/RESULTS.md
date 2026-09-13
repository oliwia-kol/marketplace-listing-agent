# Wynik kontrolowanego eksperymentu LoRA — 2026-09-13

## Teza i procedura

Sprawdzano, czy adapter LoRA małego modelu potrafi przekształcić wyłącznie zatwierdzone
fakty w krótki polski opis, zachowując wadę przedmiotu i nie dodając czterech jawnie
zabronionych klas twierdzeń. Zamrożony test obejmował 30 przykładów z sześciu rodzin
dokładnych wariantów produktów nieobecnych w train i validation. Powiązane modele mogą
występować w innych splitach, więc nie jest to test generalizacji do całkiem nowej kategorii.

Baseline uruchomiono na tym samym `Qwen/Qwen3-0.6B`, tokenizerze, system promptcie i
ustawieniu `enable_thinking=False`. LoRA trenowano przez 200 iteracji na 240 przykładach;
30 przykładów służyło do validation. Adapter uczył 1,442 mln parametrów, czyli 0,242%
modelu. Maksymalna pamięć raportowana przez MLX wyniosła 1,797 GB, a finalny adapter
ma 5 779 075 bajtów.

## Wyniki zamrożonego testu

| Metryka | Model bazowy | LoRA | Szablon deterministyczny |
|---|---:|---:|---:|
| Obecność wartości faktów | 1,000 | 1,000 | 1,000 |
| Zachowanie jawnej wady | 1,000 | 1,000 | 1,000 |
| Brak czterech zakazanych fraz | 1,000 | 1,000 | 1,000 |
| Poprawny format opisowy | 0,000 | 1,000 | 1,000 |
| Podobieństwo do referencji | 0,375 | 1,000 | 1,000 |
| Średnia latencja | 1,091 s | 1,025 s | pomijalna |

Model bazowy powtarzał wejściowy JSON zamiast pisać opis. LoRA odtworzyła oczekiwany
format we wszystkich 30 przypadkach. Validation loss spadł z 2,580 do 0,005, lecz
nie jest samodzielnym dowodem generalizacji.

## Decyzja produktowa

Adapter **nie zostaje obecnie domyślnym copywriterem**. Zbiór jest celowo syntetyczny,
ma małe zróżnicowanie stylu, a metryka zakazanych fraz nie wykrywa wszystkich możliwych
halucynacji. Co więcej, deterministyczny szablon osiąga ten sam wynik taniej i z mocniejszą
gwarancją w tym wąskim zadaniu.

Eksperyment jest wartościowym dowodem technicznym: obejmuje hipotezę, baseline,
family-level split, zamrożony test, rzeczywisty trening na GPU, kontrolę pamięci,
reprodukowalne parametry i decyzję opartą na wyniku. Następna iteracja ma sens dopiero
po zebraniu zaakceptowanych, zanonimizowanych przykładów rzeczywistych i przygotowaniu
szerszej oceny semantycznej.

## Ograniczenia

- Dane są syntetyczne i mają jeden styl referencyjny.
- String matching nie rozpoznaje wszystkich parafraz ani subtelnych halucynacji.
- Test mierzy generowanie opisu, a nie wycenę, routing, research ani publikację.
- Binarny adapter pozostaje lokalnym artefaktem ignorowanym przez Git; raport zapisuje
  jego rozmiar i SHA-256.
