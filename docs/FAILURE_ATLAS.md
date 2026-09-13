# Atlas awarii modeli i zabezpieczeń

Dokument opisuje porażki zaobserwowane 13 września 2026 na syntetycznych goldenach.
Nie są to hipotetyczne zagrożenia. Surowe raporty pozostają lokalne w `reports/`.

| Warstwa | Zaobserwowany błąd | Ryzyko | Ochrona produkcyjna | Pozostała luka |
|---|---|---|---|---|
| ekstrakcja faktów | dodatkowe lub brakujące pola | błędna identyfikacja i research | schemat, jawna akceptacja każdego faktu | człowiek może zaakceptować błąd |
| copywriter | dopisana sprawność i brak wpływu wady | wprowadzające w błąd ogłoszenie | reguły, audytor, bezpieczny szablon, akceptacja | parafraza spoza reguł może ominąć prosty guard |
| copywriter | dopisane pudełko, ładowarka, bateria lub kabel | obietnica nieistniejącego kompletu | rozszerzony guard akcesoriów i fallback | pełna semantyka wymaga lepszego groundedness eval |
| copywriter | dodatkowy portal i lokalizacja | działanie poza wyborem użytkownika | filtrowanie do requested portals; pola transakcyjne zerowane | klasyfikacja kategorii nadal wymaga przeglądu |
| audytor | poprawna decyzja OLX plus zmyślona decyzja Allegro | złamanie kontraktu liczności | aplikacja iteruje tylko rzeczywiste drafty | benchmark nadal słusznie oznacza contract failure |
| model bazowy LoRA | powtarzanie JSON zamiast prozy | bezużyteczny format | schema/format eval i porównanie z szablonem | syntetyczny test nie mierzy naturalności realnych ofert |
| wywołanie modelu | możliwość zawieszenia bez limitu | zablokowany workflow | limit czasu per rola i metadane błędu | timeout nie rozstrzyga jakości częściowej odpowiedzi |

## Przypadek: „nie wpływa na funkcjonalność”

Model dostał fakt o rysie, ale dopisał, że rysa nie wpływa na funkcjonalność. To nie
jest neutralna parafraza wady, tylko nowe twierdzenie o działaniu. Pydantic przyjął
odpowiedź, bo typy były poprawne. Guard wykrywa rdzenie `sprawn`, `działa`, frazę
`nie wpływa na` i podobne twierdzenia. Przy znalezisku graf zastępuje cały opis
deterministycznym szablonem z zatwierdzonych wartości.

## Przypadek: zmyślone akcesoria

W kilku odpowiedziach pojawiły się ładowarka, kabel HDMI, pudełko lub bateria, mimo że
nie istniały w faktach. Regułę rozszerzono o te klasy akcesoriów. To użyteczna warstwa
ochronna, ale nie kompletna ontologia języka polskiego. Docelowa ewaluacja semantyczna
powinna rozbijać opis na twierdzenia i dla każdego wskazywać najbliższy zatwierdzony
fakt albo oznaczać brak podstawy.

## Przypadek: dodatkowa decyzja audytora

W pięciu z dwudziestu przypadków audytor poprawnie odrzucił opis OLX, po czym dopisał
bezpieczną decyzję dla Allegro Lokalnie, którego nie było w wejściu. Produkcja mapuje
decyzje po portalu i iteruje po rzeczywistych draftach, więc dodatkowy rekord nie daje
uprawnienia. Mimo to benchmark ocenia `exact_portals=0`, ponieważ zgodność kontraktu
jest niezależną własnością jakości.

## Jak czytać wynik benchmarku

Porażka surowego generatora nie oznacza automatycznie porażki całego pipeline. Trzeba
osobno mierzyć generator, audytora, guard deterministyczny i wynik po fallbacku.
Jednocześnie dobry wynik pipeline nie usprawiedliwia słabego generatora: częsty fallback
obniża jakość języka i jest sygnałem do zmiany modelu, promptu lub zakresu zadania.
