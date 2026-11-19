"""OCR remains offline even when local model files are missing or corrupt."""
import pytest

from lolhex.vision.ocr import LOCAL_MODELS, OCR, local_model_params


def test_missing_and_corrupt_models_fail_without_download(tmp_path, no_network):
    with pytest.raises(RuntimeError, match='不会自动联网下载'):
        local_model_params(tmp_path)
    for name, _ in LOCAL_MODELS.values():
        (tmp_path / name).write_bytes(b'broken')
    with pytest.raises(RuntimeError, match='模型缺失或损坏'):
        local_model_params(tmp_path)


def test_runtime_telemetry_disabled_before_creating_ocr(monkeypatch, no_network):
    import onnxruntime
    import rapidocr
    calls = []
    monkeypatch.setattr(onnxruntime, 'disable_telemetry_events', lambda: calls.append('disable'))
    monkeypatch.setattr(rapidocr, 'RapidOCR', lambda params: calls.append(params))
    OCR()
    assert calls[0] == 'disable'
    assert all(calls[1][f'{section}.model_path'].endswith(name) for section, (name, _) in LOCAL_MODELS.items())
