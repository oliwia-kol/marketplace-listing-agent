# ADR 0003: cena z dowodów i statystyki deterministycznej

Status: przyjęta.

Kontekst: sama sugestia LLM nie jest wiarygodną wyceną. Decyzja: model tworzy plan i
ocenia porównywalność, weryfikator potwierdza dostępność/cenę, Python liczy statystyki,
użytkowniczka wybiera. Linki surowe są tymczasowe; w karcie zostaje agregat.
Konsekwencje: audytowalna rekomendacja, lecz aktywne ceny ofertowe nie są cenami
transakcyjnymi, a źródła mogą blokować ruch lub zmieniać DOM.
