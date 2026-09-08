# Roadmap projektu

## P0 — przed pierwszą prawdziwą publikacją

- skonfigurować prywatny Telegram i wykonać próbę na testowym przedmiocie;
- ręcznie przetestować adapter każdego formularza bez kliknięcia publikacji;
- dodać po pięć ręcznie oznaczonych goldenów: Fujifilm X, Switch, gry i Apple;
- ustalić politykę usuwania zdjęć oraz checkpointów;
- wykonać threat-model review według `docs/SECURITY.md`.

## P1 — dowód jakości do portfolio

- dashboard raportów modeli: jakość, czas, tokeny, fallback i RAM;
- wersjonowanie profili kategorii oraz ekstraktorów;
- podpisany rekord integralności bez zachowywania pełnych linków;
- testy kanarkowe portali i alert driftu DOM/odsetka kwarantanny;
- macierz testów indirect prompt injection i złośliwych URL-i;
- SBOM, skan zależności i automatyczne testy bezpieczeństwa w CI.

## P2 — odporność pomiaru

- niezależny odczyt kontrolny reprezentatywnej próbki w zwykłym Chrome;
- per-portalowe reguły zgodności widocznego DOM, JSON-LD i odpowiedzi sieciowej;
- analiza duplikatów, sprzedawców i anomalii rozkładu cen;
- porównanie cen aktywnych i jawnie sprzedanych bez mieszania ich znaczenia;
- eksperyment ablation: wynik bez i z każdą bramką bezpieczeństwa.

## P3 — hardening lokalny

- szyfrowanie danych w spoczynku i backup z testem odtworzenia;
- egress allowlista procesu researchowego;
- podpisy/sumy modeli i artefaktów; kontrolowana aktualizacja zależności;
- playbook reakcji na ujawnienie tokenu i podejrzane konto;
- okresowy przegląd regulaminów i zakresu dozwolonej automatyzacji.

Każdy punkt przechodzi ze statusu „plan” do „implemented” dopiero z kodem, testem i
dowodem wykonania. Roadmapa nie jest deklaracją gotowej funkcji.
