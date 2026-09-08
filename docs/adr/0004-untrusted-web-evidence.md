# ADR 0004: Treść internetowa jest niezaufanym dowodem

## Status

Przyjęte.

## Kontekst

Research otwiera linki odkryte na publicznych stronach. Link może prowadzić do sieci
lokalnej, treść może zawierać prompt injection, a serwer może dynamicznie zmieniać
cenę lub stronę dla automatyzacji.

## Decyzja

Stosujemy URL/DNS policy przed i po przekierowaniu, minimalizujemy dane przekazywane
do modelu, nie dajemy modelowi narzędzi, porównujemy strukturalne kanały ceny i
ponownie weryfikujemy kandydatów wybranych do statystyki. Niespójność oznacza
kwarantannę i `comparable=false`. Publikacja pozostaje ręczna.

## Konsekwencje

Badanie wykonuje więcej żądań i może konserwatywnie odrzucić legalnie zmienioną
ofertę. W zamian wynik cenowy nie korzysta z dowodu, którego integralności nie udało
się potwierdzić. Detekcja nie dowodzi złośliwej intencji i nie rozwiązuje spójnego
cloakingu skierowanego przeciw każdej automatyzacji; ograniczenie jest dokumentowane.
