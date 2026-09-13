# Macierz kompetencja → implementacja → dowód

| Kompetencja | Implementacja | Dowód | Uczciwy poziom na dziś |
|---|---|---|---|
| Agentic workflow | jawny graf, interrupts, replay | testy integracyjne grafu | implemented and tested locally |
| Trwały kontekst | SQLite + checkpointy + wąski prompt | restart repository tests | implemented and tested locally |
| Bezpieczeństwo AI | allowlist, SSRF, redakcja, HITL | regresje security | implemented and unit-tested |
| Evidence-based pricing | kanały DOM/JSON-LD/meta i bramka | fixtures OLX/Allegro | tested on redacted fixtures |
| Model routing | role, fallback, structured output | router tests i doctor | implemented; local models installed |
| Observability | metadata-only RunEvent i HTML | privacy report test | implemented locally |
| CI/CD basics | GitHub Actions i Dependabot | workflow w repo | configured; requires push to observe run |
| Packaging | wheel z zasobami i app directory | clean-venv smoke test | verified outside checkout |
| Browser automation | exact labels, readback, interventions | fake/fixture tests | real logged-in controls not yet validated |
| Docker | non-root/read-only Compose, egress proxy | build, container doctor, positive/negative egress checks | infrastructure boundary verified locally |
| MCP | SDK v2, stdio, narrow tools | facade security tests | implemented locally |
| LoRA | 300 pairs, MLX, frozen test | adapter hash + reports | trained/evaluated on synthetic data |
| Real publication | two approvals, guarded submit, reconciliation | state-machine tests | not executed on a real account |

Formułowanie CV powinno odpowiadać ostatniej kolumnie. Po controlled-browser testach i
pojedynczej zatwierdzonej publikacji można podnieść poziom tylko dla konkretnie
sprawdzonego portalu i daty.
