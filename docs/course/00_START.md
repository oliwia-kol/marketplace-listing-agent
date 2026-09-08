# Kurs: LangGraph na działającym projekcie

## Jak pracować

To nie jest kurs „przepisz kod”. Każda lekcja ma cztery kroki:

1. zrozum pojęcie;
2. znajdź je w produkcyjnym przepływie;
3. zmień mały fragment;
4. udowodnij testem lub raportem, że rozumiesz skutek.

Kolejność czytania:

1. [platforma i mapa systemu](01_PLATFORMA.md),
2. [stan, node i edge](02_GRAF.md),
3. [interrupt i checkpoint](03_HITL.md),
4. [modele lokalne i RAM](04_MODELE.md),
5. [research oraz cena](05_RESEARCH.md),
6. [sterowanie Chrome](06_BROWSER.md),
7. [ewaluacja](07_EWALUACJA.md),
8. [obrona architektury](08_OBRONA.md),
9. [cybersecurity i dynamic cloaking](09_CYBERSECURITY_CLOAKING.md).

Po każdej lekcji wykonaj `uv run pytest`. Po lekcjach modelowych uruchom właściwy
zestaw `marketplace-listing-agent eval`. Swoje wnioski zapisuj w nowym `docs/lab-notes.md`; nie
przepisuj wyniku modelu, tylko interpretuj kompromis jakość–czas–pamięć.

## Projekt zaliczeniowy

Dodaj nowy punkt akceptacji „stan przedmiotu”, przetestuj wznowienie po restarcie,
porównaj dwa modele dla jednej roli, dodaj pięć własnych goldenów i wykonaj test
jednego adaptera na żywej stronie bez publikacji. Rezultatem ma być ADR, raport JSON
i krótka notatka o tym, co nie zadziałało.
