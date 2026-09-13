from pathlib import Path

from marketplace_agent.monitoring.report import write_run_report


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
