# Ocena opisów na zanonimizowanych danych publicznych — 2026-09-14

## Pytanie eksperymentu

Celem było sprawdzenie, który lokalny model najwierniej zamienia zatwierdzone fakty w
opis OLX i Allegro Lokalnie. To ocena surowego generatora. Produkt nadal używa
łańcucha: generator → reguły → niezależny audyt → jedna naprawa → bezpieczny szablon
→ akceptacja człowieka.

## Dane i granica dowodu

Zebrano 30 publicznych przykładów: po 10 dotyczących Nintendo Switch, iPhone 13 i
obiektywów Fujifilm. Do goldenów trafiły wyłącznie znormalizowane twierdzenia z ofert,
portal i hash URL. Usunięto URL, cenę źródłową, nazwę sprzedawcy, lokalizację, kontakt
oraz pełny tekst ogłoszenia. Pole `price_pln=1` jest neutralnym placeholderem wymaganym
przez schemat. Prywatny manifest źródeł pozostaje w ignorowanym przez Git katalogu
`data/`.

Te dane opisują **twierdzenia sprzedających**. Nie dowodzą rzeczywistego stanu
przedmiotów i nie zastępują zdjęć własnych rzeczy ani etykiet zatwierdzonych przez
właścicielkę projektu. Eksporter `scripts/export_real_copy_eval.py` wymusza tę granicę
i nie pozwala przenieść do publicznego goldena typowych pól identyfikujących.

## Protokół

- split: `real_validation`;
- temperatura 0,2, `top_p=0,9`, `top_k=20`, seed 42;
- dokładnie ten sam brief i schemat odpowiedzi;
- fallback modelu wyłączony, aby wynik należał do wskazanego modelu;
- metryki: kompletność wymaganych faktów, guard niepodpartych twierdzeń, komplet
  portali, poprawność schematu oraz czas;
- przypadek przechodzi, gdy każda metryka ma co najmniej 0,8.

## Wyniki pełnych 30 przypadków

| Model | Passed | Recall faktów | Guard | Portale | Schemat | Śr. czas | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5 9B | 14/30 | 0,858 | 0,767 | 1,000 | 1,000 | 12,84 s | 15,41 s |
| Bielik 11B v3 Q4 | 3/30 | 0,787 | 0,200 | 1,000 | 1,000 | 16,60 s | 20,08 s |

Qwen 9B jest obecnie lepszym kandydatem na generator domyślny. Ten wynik nie oznacza,
że surowy opis można publikować: 16 z 30 przypadków nie spełniło całej bramki.

## Screening Qwen3.5 27B

Większy model uruchomiono na zbalansowanych dziewięciu przypadkach: po trzy z każdej
rodziny. Na identycznym podzbiorze:

| Model | Passed | Recall faktów | Guard | Śr. czas | Maks. czas |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B | 4/9 | 0,848 | 0,778 | 13,14 s | 15,41 s |
| Bielik 11B v3 Q4 | 1/9 | 0,735 | 0,333 | 16,93 s | 22,27 s |
| Qwen3.5 27B | 5/9 | 0,858 | 0,667 | 58,14 s | 83,53 s |

27B dał tylko jedno dodatkowe zaliczenie, miał słabszy guard od 9B i był około 4,4
raza wolniejszy. Pełny przebieg zatrzymano zgodnie z sekwencyjnym projektem
eksperymentu. Model może być później testowany jako eskalacja dla trudnych przypadków,
ale obecne dane nie uzasadniają użycia go domyślnie.

## Korekta błędu miernika

Pierwsza wersja guarda uznawała słowo „bateria” za niepodparte, gdy dowód znajdował
się pod typowanym kluczem `attribute.battery_health`. Regułę poprawiono i objęto testem
regresji. Surowe raporty zachowano, a skrypt `scripts/rescore_copy_report.py` utworzył
nowe raporty z:

- pierwotnymi metrykami przy każdym przypadku;
- hashami raportu źródłowego i datasetu;
- timestampem i commitem wersji scorera.

To ważna lekcja: monitoring modelu sam jest oprogramowaniem i może wprowadzać błąd
pomiaru. Wynik bez wersjonowania danych, promptu i scorera nie jest audytowalny.

## Ślepa ocena językowa

`scripts/build_blind_copy_review.py` utworzył lokalny pakiet dziewięciu przypadków
A/B/C. Kolejność wariantów jest losowana deterministycznie, nazwy modeli są w osobnym
kluczu, odpowiedzi zapisują się w `localStorage`, a przycisk eksportuje oceny JSON.
Rubryka obejmuje naturalność, jasność, wiarygodność faktów, dopasowanie do portalu,
użyteczność i veto bezpieczeństwa.

Pakiet i klucz znajdują się w `reports/`, który jest ignorowany przez Git. Prawdziwa
ocena człowieka pozostaje świadomie niewypełniona: automatyczna lub wykonana przez
asystenta nie byłaby dowodem preferencji użytkowniczki.

## Decyzja wykonawcza

1. Zmienić generator domyślny z Bielika 11B na Qwen3.5 9B. Jest to wybór modelu
   surowego generatora; obowiązkowy audyt i fallback pozostają bez zmian.
2. Nie wdrażać LoRA. Aktualny błąd dotyczy głównie wierności faktom, a nie samego
   stylu lub formatu.
3. Następny dataset budować z własnych zdjęć i zatwierdzonych notatek, rozdzielając
   rodziny produktów między development, selection i frozen.
4. Raportować osobno jakość surowego generatora, skuteczność audytora, częstość
   naprawy/fallbacku oraz ślepą ocenę człowieka.
