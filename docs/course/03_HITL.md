# 3. Human-in-the-loop: interrupt i checkpoint

`interrupt(payload)` przerywa node i oddaje serializowalny payload do kanału.
Checkpointer zapisuje stan. `Command(resume=value)` wznawia ten sam `thread_id`, a
wartość staje się wynikiem `interrupt`.

Najważniejszy szczegół: przy wznowieniu node zaczyna się od początku. Dlatego:

- inferencja jest w poprzednim node;
- przed `interrupt` nie wysyłamy wiadomości ani nie zmieniamy zewnętrznego systemu;
- kolejność interruptów w pętli po faktach jest stała;
- side effect zapisu preferencji występuje dopiero po zebraniu decyzji.

Test `tests/test_workflow.py` uruchamia graf i sześć razy sprawdza rodzaj pauzy. Nie
testuje modelu ani portalu — testuje kontrakt procesu. `InMemorySaver` jest właściwy
dla testu; aplikacja używa trwałego `AsyncSqliteSaver`.

## Ćwiczenie

Uruchom test z `-vv`, zmień kolejność dwóch edges i zobacz, który assertion ujawni
naruszenie. Następnie odtwórz poprawną kolejność. Wyjaśnij własnymi słowami różnicę
między katalogiem przedmiotów a checkpointem wykonania.
