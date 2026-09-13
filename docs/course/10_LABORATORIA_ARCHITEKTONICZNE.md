# Laboratoria architektoniczne

Te ćwiczenia służą rozumieniu mechanizmów, nie przepisywaniu kodu. Każde laboratorium
ma pięć części: hipotezę, eksperyment, obserwację, wyjaśnienie oraz granicę dowodu.
Własne wyniki zapisuj w `docs/lab-notes.md`.

## Laboratorium 1 — model bez pamięci

**Hipoteza:** po restarcie model niczego nie „pamięta”, ale aplikacja odtwarza sprawę z
SQLite i checkpointu.

1. Uruchom przypadek do pierwszego `interrupt`.
2. Zanotuj `item_id`, wyłącz proces i uruchom go ponownie.
3. Wywołaj `/status` i wznów ten sam krok.
4. W SQLite odszukaj `channel_sessions`, `conversation_notes` i checkpoint.

Wyjaśnij różnicę między pamięcią procesu, trwałym stanem domenowym i pozycją grafu.
Test integracyjny potwierdza mechanizm lokalnie; nie dowodzi jeszcze odporności na
uszkodzenie dysku.

## Laboratorium 2 — transakcja i wyścig dwóch workerów

**Hipoteza:** `BEGIN IMMEDIATE` oraz warunkowy `UPDATE` pozwolą tylko jednemu workerowi
przejąć job.

Uruchom test `test_engine_is_idempotent_and_moves_job_to_ready`, a następnie przeczytaj
`claim_next_execution`. Narysuj stan przed transakcją, blokadę zapisu i stan po commit.
Wyjaśnij, dlaczego sam odczyt, a potem osobny zapis bez transakcji tworzyłby race
condition.

## Laboratorium 3 — awaria podczas submit

**Hipoteza:** ten sam watchdog powinien inaczej potraktować etap `preparing` i
`submitting`.

Uruchom test `test_stale_prepare_is_requeued_but_stale_submit_is_never_retried`.
Przygotowanie jest odwracalne, więc wraca do kolejki. Submit mógł dotrzeć do portalu,
dlatego przechodzi do `unknown`. Wyjaśnij, czemu lokalne idempotency nie daje
`exactly-once` w systemie zewnętrznym bez wspólnego klucza idempotency.

## Laboratorium 4 — zmiana jednego bajtu zdjęcia

**Hipoteza:** zgoda na podgląd nie może autoryzować później zmienionego pliku.

Uruchom testy `test_snapshot_is_content_addressed_and_detects_changed_photo` oraz
`test_adapter_rechecks_photo_hash_at_each_boundary`. Porównaj hash logiczny payloadu z
hashem bajtów pliku. Wyjaśnij, dlaczego nazwa `01.jpg` nie jest dowodem tożsamości.

## Laboratorium 5 — niebezpieczna cena

**Hipoteza:** przesyłka, rata, stara cena i obca waluta nie mogą wejść do mediany.

Uruchom testy pricingu i narysuj kolejność: ekstrakcja obserwacji, porównanie kanałów,
kwalifikacja, deduplikacja, statystyka. Usuń na lokalnej gałęzi jedną bramkę, uruchom
test, zapisz rodzaj fałszywego wyniku i cofnij zmianę.

## Laboratorium 6 — poprawny JSON, błędna treść

**Hipoteza:** walidacja Pydantic potwierdzi strukturę, lecz przepuści zmyślone akcesoria.

Przeczytaj przypadki w `FAILURE_ATLAS.md`, uruchom `test_copy_safety.py` i porównaj:

- surowy szkic Bielika;
- decyzję audytora;
- wynik `obvious_unsupported_claims`;
- `safe_template`.

Wyjaśnij defense in depth i wskaż, której klasy parafraz prosty string matching nadal
nie rozpozna.

## Laboratorium 7 — benchmark bez ukrytego fallbacku

**Hipoteza:** fallback może sztucznie zawyżyć wynik modelu, który faktycznie zawiódł.

Uruchom dwa razy jeden mały suite: raz dla dostępnego modelu, raz dla nieistniejącego
tagu. Sprawdź raport: model, error type, hash datasetu i `fallback_policy`. Wyjaśnij,
dlaczego test produktu może mieć fallback, a porównanie modeli powinno go wyłączać.

## Laboratorium 8 — MCP jako interfejs, nie autoryzacja

Uruchom test `test_mcp_facade.py`. Dla każdego narzędzia zapisz: wejście, odczytywaną
tabelę, możliwą zmianę stanu i ponownie sprawdzany warunek. Spróbuj zaprojektować
niebezpieczne narzędzie `publish(title, price, cookie)` i wskaż, które granice łamie.

## Laboratorium 9 — Docker i SSRF

Uruchom `docker compose config` oraz test `test_egress_proxy.py`. Wyjaśnij kolejno:
wewnętrzną sieć, proxy, rozwiązywanie DNS, odrzucenie adresów specjalnych i połączenie
z już zweryfikowanym IP. Gdy Docker Desktop działa, zbuduj obraz i sprawdź, czy kontener
nie widzi pliku kontrolnego z katalogu domowego.

## Laboratorium 10 — LoRA i decyzja o niewdrożeniu

Odtwórz wyniki z `experiments/lora/RESULTS.md`. Rozdziel trzy pytania:

1. Czy optymalizacja zbiegała? — odpowiada loss.
2. Czy model działa na zamrożonym teście? — odpowiadają metryki testowe.
3. Czy warto go wdrożyć? — wymaga porównania z prostszym szablonem i danych realnych.

Obrona eksperymentu polega na wykazaniu, że dobry wynik treningu nie wymusza decyzji
produktowej.

## Schemat odpowiedzi na rozmowie

Dla każdej decyzji stosuj kolejność:

1. problem i skutek błędu;
2. wybrany mechanizm;
3. rozważana alternatywa i koszt;
4. dowód z testu albo raportu;
5. uczciwa granica tego dowodu.

Przykład: „Przerwany submit zapisuję jako `unknown`, ponieważ portal mógł przyjąć
żądanie mimo utraty odpowiedzi. Automatyczny retry grozi duplikatem. Test stanu workera
potwierdza lokalną politykę, ale zachowanie aktualnego OLX wymaga kontrolowanej próby na
zalogowanym koncie”.
