from pathlib import Path

from marketplace_agent.monitoring.report import write_copy_report, write_run_report


def test_report_allow_lists_metadata_and_escapes_html(tmp_path: Path) -> None:
    path = write_run_report(
        [
            {
                "created_at": "now",
                "component": "model<script>",
                "operation": "copy",
                "status": "ok",
                "payload": {"model": "qwen", "prompt": "do-not-render", "prompt_tokens": 9},
            }
        ],
        tmp_path,
        "run-1",
    )
    report = path.read_text()
    assert "do-not-render" not in report
    assert "&lt;script&gt;" in report
    assert "prompt_tokens" in report


def test_copy_report_contains_local_stages_and_escapes_content(tmp_path: Path) -> None:
    path = write_copy_report(
        [
            {
                "stage": "draft",
                "portal": "olx",
                "created_at": "now",
                "payload": {"description": "Rysa <script>"},
            }
        ],
        tmp_path,
        "run-copy",
        [
            {
                "naturalness": 4,
                "clarity": 5,
                "factual_trust": 5,
                "portal_fit": 4,
                "usefulness": 4,
            }
        ],
    )

    report = path.read_text()
    assert "Rysa" in report
    assert "&lt;script&gt;" in report
    assert "<script>" not in report
    assert 'Etapy: {&quot;draft&quot;: 1}' in report
    assert "Oceny człowieka: 1" in report
