# 2. Stan, node i edge

## Definicje

**State** to serializowalny zapis wiedzy procesu. **Node** to funkcja `state → update`.
**Edge** wskazuje następny node. `START` i `END` są umownymi krańcami grafu.

W `workflow/state.py` stan jest `TypedDict`, a `item` jest zwykłym słownikiem. Na
granicy node'a Pydantic odtwarza `ItemCase`. Dzięki temu checkpoint przechowuje proste
dane, a logika domenowa nadal ma typy i walidację.

## Dlaczego graf jawny

Proces biznesowy ma znaną kolejność. Autonomiczne wybieranie kolejnego narzędzia przez
LLM nie daje tu wartości; zmniejsza przewidywalność. Jawne edges pokazują podczas
code review, czy np. formularz może zostać wypełniony przed akceptacją ceny.

## Przykład node'a

`research_price` bierze zatwierdzone fakty, woła usługę research i zwraca nowe pole
`price_summary`. Nie formatuje Telegrama i nie wypełnia formularza. Ta pojedyncza
odpowiedzialność pozwala podstawić `ResearchStub` w teście całego grafu.

## Ćwiczenie

Dodaj status `RESEARCH_FAILED` i warunkową krawędź pozwalającą użytkowniczce ponowić
research. Najpierw napisz test. Zastanów się, które błędy są przejściowe, a które
wymagają zmiany faktów.
