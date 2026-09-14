# Wynik eksperymentu LoRA v2 — 2026-09-14

## Pytanie

Czy LoRA dla `Qwen/Qwen3-0.6B` nauczy mały model pisać naturalny polski opis na
podstawie niepełnych faktów i zachować dane dla kategorii niewidzianych w treningu?

## Metoda

- 600 własnych, syntetycznych przykładów: 400 train, 100 validation, 100 frozen test;
- osiem rodzin w train, router i robot kuchenny w validation, suszarka i
  wiertarko-wkrętarka wyłącznie w frozen test;
- MLX-LM 0.30.7 i MLX 0.32.2;
- model bazowy `Qwen/Qwen3-0.6B`, osiem końcowych warstw, learning rate `1e-5`;
- 300 iteracji, batch 1, akumulacja gradientu 4, maskowanie promptu;
- porównane rank 8 i rank 16, wspólny seed `20260914`.

Adapter rank 8 uczył 1,442 mln parametrów (0,242%) i użył maksymalnie 1,797 GB
pamięci. Rank 16 uczył 2,884 mln (0,484%) i użył 1,830 GB. Końcowy validation loss
wyniósł odpowiednio 0,027 i 0,017.

## Frozen test: 100 przypadków

| Metryka | Model bazowy | LoRA rank 8 | LoRA rank 16 |
|---|---:|---:|---:|
| Pokrycie dokładnych wartości faktów | 0,990 | 0,803 | 0,808 |
| Zachowanie nazwy przedmiotu | 1,000 | 0,500 | 0,500 |
| Zachowanie podanej wady | 1,000 | 1,000 | 1,000 |
| Guard jawnych zakazanych fraz | 1,000 | 1,000 | 1,000 |
| Format prozy | 0,000 | 1,000 | 1,000 |
| Poprawna granica po zwrocie otwierającym | 1,000 | 0,530 | 0,550 |
| Mediana czasu | 0,787 s | 0,814 s | 0,826 s |
| p95 czasu | 1,129 s | 1,192 s | 1,199 s |

Model bazowy najczęściej kopiował JSON, dlatego jego pokrycie faktów jest wysokie,
ale wynik nie jest użytecznym opisem. Oba adaptery nauczyły się prozy. Jednocześnie
na niewidzianych rodzinach sklejały czasownik z nazwą, np. tworzyły formy podobne do
`Sprzedajęuszarkę`, i w połowie przypadków nie zachowywały dokładnej nazwy przedmiotu.
Rank 16 nie naprawił problemu rank 8.

## Decyzja

Żaden adapter v2 nie wchodzi do runtime. Validation loss poprawiał się, lecz jakość
użytkowa na frozen test pogorszyła się. To jest wartościowy wynik negatywny: pokazuje,
że loss mierzy przewidywanie tokenów w zbiorze, a nie automatycznie wierność ani
poprawność językową dla nowej kategorii.

Kolejna iteracja wymaga najpierw bardziej różnorodnych, ręcznie sprawdzonych tekstów i
naprawy konstrukcji danych gramatycznych. Nie należy zwiększać modelu lub liczby
iteracji bez nowej hipotezy. Qwen3.5 9B pozostaje copywriterem aplikacji.

## Powtarzalność i granice

- SHA-256 train: `381ce81614ce11f9bff765d3c5241d8bc9dd0416dce8137a081e5ea3a7ac4567`;
- SHA-256 validation: `a1039eb709f1fcb01d406202f17edb3321e4c11107efefbdf7100a607d6e3a0f`;
- SHA-256 frozen test: `079d701ee13dc69ac0ca2960b02bbe3c84d6be9a9b4ae3ab27193e2c3961dab1`;
- adapter rank 8: `106a118e7f104eed27c99d4221a2595b72e1491ab5934a26241e1bfda29df242`;
- adapter rank 16: `344abb3dd54737ca641c6510ff92f73b8d6b3b6a3557693cf2f47eb1d70306d3`.

Metryki oparte na ciągach znaków nie wykrywają wszystkich parafraz ani halucynacji.
Dataset nie był ręcznie oceniany przez użytkowniczkę i nie jest dowodem jakości na jej
przedmiotach. Binaria adapterów pozostają lokalne i są ignorowane przez Git.
