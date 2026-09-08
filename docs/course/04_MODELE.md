# 4. Modele lokalne, role i pamięć

**Model routing** oznacza wybór modelu według rodzaju zadania, nie według dowolnej
decyzji agenta. `config/models.yaml` jest policy file. Kod zna rolę, a konfiguracja
przypisuje jej konkretny tag modelu i fallback.

`OllamaModelProvider` robi pięć rzeczy: koduje zdjęcia, przekazuje JSON Schema,
ustawia temperaturę zero, blokuje równoległość i ustawia krótki `keep_alive`. Pydantic
ponownie waliduje odpowiedź. Sam fakt poprawnego JSON nie oznacza poprawności
merytorycznej — to dopiero mierzą goldeny.

## Sekwencyjność i RAM

Lock zapewnia jedną inferencję naraz. Po 30 sekundach Ollama wyładowuje model. To
pozwala uruchamiać naprzemiennie model wizualny, duży audytor i Bielika. Ceną jest
ponowny czas ładowania. Raport zapisuje `load_duration_seconds` w odpowiedzi
providera, a benchmark powinien mierzyć również pamięć procesu Ollama narzędziem
systemowym.

Pierwszy rozszerzony benchmark faktów pokazał niestabilność 4B i lepszy recall 9B,
dlatego `vision_fast` używa teraz 9B z fallbackiem 4B. Nazwa roli jest historyczna;
ważniejszy jest mierzalny kontrakt zadania. To decyzja tymczasowa: dataset ma sześć
syntetycznych przypadków, więc nie dowodzi jeszcze jakości na prawdziwych zdjęciach.

## Ćwiczenie

Uruchom `copy` na Bieliku i na Qwenie z `--model`. Nie wybieraj zwycięzcy po jednym
ładnym tekście. Dodaj co najmniej pięć trudnych przypadków, oceń ślepo pary i sprawdź
guard halucynacji. Zapisz, przy jakim zysku jakości akceptujesz dłuższą inferencję.
