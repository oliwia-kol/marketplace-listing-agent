# 5. Research i evidence-based pricing

Crawler to mechanizm odwiedzania wielu stron według reguł. W tym projekcie Playwright
pełni rolę crawl/render engine, a własne klasy rozdzielają discovery, ekstrakcję i
weryfikację. Crawlee byłby sensowny przy większej skali, kolejkach i rozbudowanej
polityce retry; dla jednego przedmiotu naraz zwiększałby liczbę technologii bez
koniecznej korzyści.

Model nie liczy średniej. Najpierw proponuje zapytania, potem ocenia semantyczną
porównywalność. Kod deterministyczny liczy statystykę tylko z rekordów
`verified=True` i `comparable=True`.

P25 sugeruje szybszą sprzedaż, mediana cenę rynkową, P75 cierpliwe oczekiwanie.
Średnia przycięta pokazuje środek mniej czuły na skrajności. Confidence zależy od
liczby ofert i różnorodności źródeł; nie jest pewnością, że przedmiot się sprzeda.

Profil kategorii dopowiada, które warianty są cenowo istotne. Przed nawigacją URL
przechodzi kontrolę publicznego DNS, a przed statystyką zaakceptowany kandydat jest
otwierany drugi raz. Niespójność oznacza kwarantannę. Szczegóły i ograniczenia są w
lekcji 9.

## Ćwiczenie

Dodaj golden z jedną ceną 10 razy wyższą. Przewidź medianę i średnią przyciętą przed
uruchomieniem. Potem dodaj koszt dostawy do polityki ceny i zdecyduj, czy porównujesz
cenę produktu, czy koszt całkowity — obie odpowiedzi są możliwe, ale muszą być jawne.
