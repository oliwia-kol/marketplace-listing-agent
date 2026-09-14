# Kurs: LangGraph na działającym projekcie

Pełna wersja wykładowa znajduje się w
[`PODRECZNIK_TECHNICZNY.md`](PODRECZNIK_TECHNICZNY.md), a prowadzony przepływ kodu w
[`../WALKTHROUGH.md`](../WALKTHROUGH.md). Ten plik jest krótkim indeksem ćwiczeń.

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
9. [cybersecurity i dynamic cloaking](09_CYBERSECURITY_CLOAKING.md),
10. [laboratoria architektoniczne](10_LABORATORIA_ARCHITEKTONICZNE.md),
11. [wiarygodny opis oferty](11_WIARYGODNY_OPIS_OFERTY.md).
12. [generalizacja i LoRA v2](12_GENERALIZACJA_I_LORA_V2.md).

Rzeczywiste porażki modeli i odpowiadające im zabezpieczenia opisuje
[`../FAILURE_ATLAS.md`](../FAILURE_ATLAS.md), a wyniki 120 przypadków i LoRA są w
[`../EVALUATION_RESULTS_2026-09-13.md`](../EVALUATION_RESULTS_2026-09-13.md). Nową
warstwę copy i jej ograniczenia zapisuje
[`../IMPLEMENTATION_LOG_2026-09-14.md`](../IMPLEMENTATION_LOG_2026-09-14.md).

Po każdej lekcji wykonaj `uv run --no-editable pytest`. Po lekcjach modelowych uruchom właściwy
zestaw `marketplace-listing-agent eval`. Swoje wnioski zapisuj w nowym `docs/lab-notes.md`; nie
przepisuj wyniku modelu, tylko interpretuj kompromis jakość–czas–pamięć.

## Projekt zaliczeniowy

Dodaj nowy punkt akceptacji „stan przedmiotu”, przetestuj wznowienie po restarcie,
porównaj dwa modele dla jednej roli, dodaj pięć własnych goldenów i wykonaj test
jednego adaptera portalu na żywej stronie bez publikacji. Rezultatem ma być ADR, raport JSON
i krótka notatka o tym, co nie zadziałało.
