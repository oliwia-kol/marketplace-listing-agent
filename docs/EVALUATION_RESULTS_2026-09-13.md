# Ewaluacja modeli i warstw deterministycznych — 2026-09-13

## Cel i granice dowodu

Ewaluacja sprawdza sześć oddzielnych kontraktów systemu. Każdy zestaw zawiera 20
syntetycznych, wersjonowanych przypadków. Modelowy fallback jest wyłączony, dlatego
wynik należy do wskazanego modelu i konfiguracji, a nie do niejawnego łańcucha modeli.
Raport zapisuje hash datasetu, hash konfiguracji, commit, środowisko, czasy i surową
odpowiedź. Dane te pozwalają odtworzyć eksperyment, ale nie zastępują próby na realnych,
ręcznie etykietowanych ofertach.

## Wyniki

| Kontrakt | Wykonawca | Wynik | Średni czas | p95 | SHA-256 datasetu |
|---|---|---:|---:|---:|---|
| `price_math` | kod deterministyczny | 20/20 | pomijalny | pomijalny | `90447f305364ebe61a99cb845079e3ca3076447dfdd4f2416cfc8ca07b1090ae` |
| `comparables` | Qwen3.5 9B | 20/20 | 17,07 s | 21,19 s | `6f98365e95f94c5d43697dc23def1fd5802c9ab3f5782a042333150ec1c78f5b` |
| `forms` | Qwen3.5 4B | 20/20 | 6,46 s | 7,36 s | `0886de4f5405830dd857380fe139d103e9e8690f78947402e184330c8b758cd5` |
| `copy_audit` | Qwen3.5 9B | 15/20 | 4,28 s | 5,00 s | `c15c1f6aa621d0533bb409b884e4b36b1d12e8350fe3c4e8f439e7816cfb9cce` |
| `copy` | Bielik 11B v3 Q4 | 7/20 | 22,40 s | 45,08 s | `c00c042af218445f8b1e0383e8f848c4101ef8ea92eeab77f0e360c8a01fed26` |
| `facts` | Qwen3.5 9B | 14/20 | 21,38 s | 31,60 s | `c20c00fe72f7960a862a5f0b57e5987ad3de5d34758677f92e7ed56e07a94020` |

`p95` policzono empirycznie z 20 obserwacji jako 19. uporządkowaną wartość. Raporty
JSON pozostają lokalne w ignorowanym katalogu `reports/`, ponieważ przyszłe przebiegi
mogą zawierać dane użytkowniczki.

## Interpretacja techniczna

`price_math` jest kontraktem czysto deterministycznym. Kod odrzuca pozycje bez pewnej
waluty, ceny, typu produktu i wiarygodnego źródła, a potem liczy statystyki. Wynik 20/20
nie dowodzi jakości ofert wejściowych; dowodzi zachowania obliczeń na znanych danych.

`comparables` uzyskał 20/20 na syntetycznych przykładach wariantów Fuji, Nintendo i
Apple oraz prób prompt injection. Pozostaje separatorem kandydatów, nie źródłem cen.
O przyjęciu ceny nadal decyduje bramka napisana w kodzie.

`forms` uzyskał 20/20 dla planów akcji na zamrożonych fixtures. Ten test pokazuje, że
planner nie zażądał niedozwolonych kliknięć. Nie dowodzi zgodności z aktualnym DOM po
zalogowaniu ani skutecznego wystawienia oferty.

`copy_audit` odrzucił bezpieczne opisy w pięciu przypadkach OLX, ponieważ dopisał drugi
portal do oczekiwanej decyzji. Jest więc konserwatywny, lecz nie w pełni skalibrowany.
Warstwa nie może samodzielnie publikować ani zatwierdzać treści.

`copy` pokazał najważniejszy negatywny wynik projektu: Bielik przechodzi 7/20 i potrafi
dopisywać sprawność, wpływ wady lub akcesoria. Dlatego generuje jedynie szkic. Niezależny
audyt, reguły wykrywające twierdzenia wysokiego ryzyka, bezpieczny szablon oraz zgoda
użytkowniczki pozostają wymagane.

`facts` po poprawieniu błędów ontologii goldenów osiągnął 14/20. Wszystkie przypadki
miały poprawny schemat i przeszły zakaz jawnych halucynacji, ale sześć nie osiągnęło
progu precyzji, recall lub zgodności wartości. Model może proponować fakty i pytania;
SQLite zapisuje je jako niezatwierdzone, a użytkowniczka jest źródłem finalnej prawdy.

## Kontrola jakości samego benchmarku

Pierwsza wersja rozszerzonego zbioru `facts` błędnie traktowała format gry jako kolor i
niespójnie łączyła pojemność urządzeń Apple z nazwą modelu. Benchmark ujawnił problem
etykiet, a nie tylko problem modelu. Ontologię poprawiono przed raportowanym przebiegiem.
Nie obniżano progów ani oczekiwań w celu podniesienia wyniku.

## Eksperyment LoRA

Na Macu M4 wykonano trening MLX-LM dla `Qwen/Qwen3-0.6B`: 240 przykładów train, 30
validation i 30 zamrożonych testów, z podziałem po rodzinie produktu. Trenowano 1,442 mln
z 596,050 mln parametrów (0,242%); szczyt pamięci wyniósł 1,797 GB. Adapter osiągnął
30/30 w wąskim zadaniu formatowania opisu, podczas gdy baza osiągnęła 0/30.

Deterministyczny szablon również osiągnął 30/30. Adapter pozostaje więc dowodem
umiejętności eksperymentalnej, ale nie został wdrożony do produktu. Ponowny fine-tuning
ma sens dopiero dla realnego błędu semantycznego, na zanonimizowanym zbiorze z osobnym
testem i porównaniem do prostszego baseline'u. Szczegółowy zapis znajduje się w
[`../experiments/lora/RESULTS.md`](../experiments/lora/RESULTS.md).

## Decyzje wykonawcze

1. Nie publikować bez zatwierdzenia faktów i dokładnego snapshotu.
2. Zachować deterministyczną bramkę cen, reguły copy safety i fallback szablonowy.
3. Nie promować LoRA do runtime na podstawie syntetycznego remisu z szablonem.
4. Zbudować kolejny dataset z realnych, zanonimizowanych przypadków oraz podwójnej
   ręcznej adnotacji; syntetyczne przypadki zachować jako regresje.
5. Mierzyć osobno jakość, bezpieczeństwo, koszt pamięci i czas każdej roli.

## Pilot większego copywritera — Qwen3.5 27B

Po zamknięciu głównego benchmarku wykonano krótki test niezmienionego promptu na
czterech pierwotnych przypadkach i lokalnym `qwen3.5:27b`. Model uzyskał 2/4 według
metryki dosłownych fraz, ale 4/4 dla zakazanych fraz. Dwie porażki wynikały z parafrazy
faktu, np. innego sposobu napisania „bez pudełka”, a nie z niepopartego twierdzenia.
Średni czas wyniósł 57,39 s, przy maksimum 83,37 s.

Pilot nie jest porównywalny z pełnym wynikiem Bielika 7/20 i nie uzasadnia zmiany modelu.
Pokazuje natomiast, że obecna metryka miesza wierność semantyczną z literalnym
dopasowaniem tekstu. Następna iteracja powinna mierzyć claim-level grounding, zachowanie
wady i kompletności oraz ocenianą w ciemno użyteczność językową.
