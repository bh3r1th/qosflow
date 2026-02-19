from qosflow.analysis.phase import detect_phase


def test_detect_phase(tmp_path):
    path = tmp_path / "metrics.csv"
    path.write_text("count,latency_ms_p50,latency_ms_p95\n10,100,200\n", encoding="utf-8")
    assert detect_phase(str(path)) == "stable"
