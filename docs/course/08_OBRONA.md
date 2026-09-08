# 8. Jak obronić architekturę

## Pytanie: po co LangGraph, skoro to liniowy proces?

Bo proces jest długotrwały, wielokrotnie czeka na człowieka i musi przetrwać restart.
Zwykły skrypt wystarczyłby do jednego przebiegu, ale wymagałby ręcznej implementacji
checkpointów, korelacji odpowiedzi i wznowień. Jeśli usuniemy HITL, LangGraph może
stać się zbędny — to uczciwe kryterium.

## Dlaczego Telegram, a nie od razu aplikacja WWW?

Telegram minimalizuje pracę nad UI i dobrze obsługuje zdjęcia oraz przyciski. Koszt:
zdjęcia przechodzą przez usługę zewnętrzną, a edycja długiego tekstu jest mniej
wygodna. Kanał jest adapterem, więc lokalne web UI można dodać później bez przebudowy
grafu.

## Dlaczego kilka modeli?

Role mają inne profile: obraz, rygor porównania, polski styl i GUI. Routing pozwala
testować tę hipotezę. Jeśli ewaluacja pokaże, że jeden model spełnia wszystkie progi,
uproszczenie będzie lepszą architekturą.

## Dlaczego AI w formularzu tylko jako fallback?

Selektor jest szybszy, tańszy i deterministyczny. AI pomaga przy zmiennym interfejsie,
ale wymaga ograniczenia akcji i odczytu kontrolnego. To użycie AI tam, gdzie wnosi
odporność, bez oddawania mu uprawnień publikacji.

## Dlaczego dwa magazyny SQLite?

Checkpoint odpowiada „gdzie jest wykonanie?”, katalog „jaki jest przedmiot?”. Można
usunąć historię grafu bez utraty karty sprzedawanego przedmiotu. Można też zmienić
orkiestrator bez migracji całej domeny.

## Ostateczny test zrozumienia

Wyjaśnij projekt bez nazw bibliotek: „kanał zbiera dane, automat stanów zatrzymuje
się przy decyzjach, wyspecjalizowane funkcje analizują, dowody cenowe są weryfikowane,
formularz wypełnia ograniczony wykonawca, a człowiek publikuje”. Dopiero potem dodaj
nazwy LangGraph, Ollama, Pydantic i Playwright.
