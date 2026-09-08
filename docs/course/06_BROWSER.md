# 6. AI i kontrola Chrome

Playwright jest wykonawcą, model jest doradcą. Najpierw próbujemy etykiet (`label`),
bo są czytelne, testowalne i często stabilniejsze niż klasy CSS. Gdy zawiodą, model
dostaje screenshot i ograniczony opis kontrolek, a zwraca `FormPlanOutput`.

To wzorzec **plan–validate–execute–verify**:

1. plan AI;
2. walidacja schematu, confidence i forbidden targets;
3. wykonanie małego słownika akcji;
4. readback wartości;
5. screenshot i ewentualne przekazanie użytkowniczce.

Model nie otrzymuje dowolnego dostępu do Playwright. `SafeActionExecutor` jest
reference monitor: każda akcja przechodzi przez jedno miejsce egzekwujące politykę.

## Ćwiczenie

Zbuduj lokalny HTML z polami o zmienionych etykietach. Najpierw dodaj test, że
selektor deterministyczny nie pasuje, potem sprawdź plan modelu. Umieść przycisk
„Opublikuj” i udowodnij testem, że nawet błędny plan go nie kliknie.
