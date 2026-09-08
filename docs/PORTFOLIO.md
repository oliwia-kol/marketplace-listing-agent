# Dowody do portfolio i CV

## Co można powiedzieć już teraz

„Zaprojektowałam i rozwijam lokalny workflow human-in-the-loop do przygotowywania
ofert sprzedażowych. Zdefiniowałam granice autonomii, model stanu LangGraph, routing
wyspecjalizowanych modeli w Ollama, evidence-based pricing oraz zabezpieczenie przed
automatyczną publikacją. Waliduję rozwiązanie testami i golden datasets.”

## Czego jeszcze nie mówić

- że system jest produkcyjny albo bezobsługowy;
- że ustala realne ceny sprzedaży, jeśli dysponuje głównie cenami ofertowymi;
- że adaptery portali są stabilne bez udokumentowanych prób na żywych formularzach;
- że model 27B jest najlepszy — próba operacyjna nie zakończyła się poprawnie;
- że Vinted oficjalnie wspiera ten sposób automatyzacji.
- że system zapewnia pełną ochronę przed cloakingiem — wykrywa określone klasy
  niespójności, a spójny cloaking wymaga niezależnego punktu obserwacji.

## Checklista dowodów przed publikacją repozytorium

- testy i lint przechodzą na czystym środowisku;
- minimum 20 ręcznie oznaczonych przypadków na każdą ocenianą rolę;
- zanonimizowane screenshoty i jeden opisany przebieg end-to-end;
- tabela porównania co najmniej dwóch modeli na niezmienionych danych;
- co najmniej jeden live research z niezerowym, ręcznie sprawdzonym zbiorem porównań;
- osobno opisane ograniczenia, awarie i interwencje użytkowniczki;
- brak `.env`, tokenów, zdjęć prywatnych, profilu Chrome i baz SQLite;
- historia Git sprawdzona pod kątem sekretów przed publicznym push.
- threat model, testy złośliwych URL-i/prompt injection i licznik kwarantanny;
- profile Fujifilm/Switch/Apple oraz goldeny rozróżniające warianty.

## Proponowane eksperymenty

| Eksperyment | Hipoteza | Metryka | Kryterium decyzji |
|---|---|---|---|
| Bielik vs Qwen copy | Bielik pisze naturalniej po polsku | ocena par + hallucination guard | ≥60% preferencji bez wzrostu błędów |
| Qwen 27B vs 9B market | 27B lepiej odrzuca pozorne porównania | F1, czas, pamięć | istotny wzrost F1 wart opóźnienia |
| selektor vs GUI AI | AI ratuje zmienione DOM | success/readback | używać tylko przy confidence ≥0.75 |
| 8 vs 15 vs 25 ofert | większa próba stabilizuje medianę | zmiana mediany/P25/P75 | zakończyć, gdy wynik się stabilizuje |

Każdy wykres i wynik powinien wskazywać commit, wersję datasetu, model/tag i datę.
