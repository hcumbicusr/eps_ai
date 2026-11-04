"""Pruebas SIN entrenar ni evaluar clasificadores."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

from src.experiments.sidi_run_003 import (
    build_pipeline,
    describe_partition,
    load_verified_dataset,
    partition_indices,
    rank_models,
    validate_config,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "protocolos/SIDI_RUN_003_config.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "protocolos/SIDI_DATA_002_manifest.json").read_text(encoding="utf-8"))


def test_protocolo_congruente():
    validate_config(CONFIG, MANIFEST)


def test_pipeline_incluye_escalado_interno():
    p = build_pipeline("XGBoost", pd.Series([0, 0, 1]), 42)
    assert [n for n, _ in p.steps] == ["scaler", "classifier"]
    assert not hasattr(p.named_steps["scaler"], "mean_")  # No ajustado antes del fold.


def test_splits_no_solapados_ni_test_en_cv():
    y = pd.Series([0] * 90 + [1] * 10)
    tr, te, folds = partition_indices(y, 42, 0.2, 5)
    assert len(tr) == 80 and len(te) == 20
    assert len(set(tr) & set(te)) == 0
    assert all(not set(v) & set(te) for _, v in folds)
    assert all(len(v) == 16 for _, v in folds)
    assert sum(x["validation"]["irregular"] for x in describe_partition(y, tr, te, folds)["folds"]) == 8


def test_rankeo_prioriza_f1_sobre_ap_y_no_consulta_test():
    names = ["A", "B"]
    rows = []
    for i in range(5):
        rows.append({"Modelo": "A", "F1": .70, "AP": .60, "Precision": .7, "Recall": .7})
        rows.append({"Modelo": "B", "F1": .69, "AP": .99, "Precision": .7, "Recall": .7})
    assert rank_models(rows, names)[0]["Modelo"] == "A"


def test_dataset_real_aportado_integridad(archivo_dataset):
    X, y = load_verified_dataset(Path(archivo_dataset), MANIFEST)
    assert X.shape == (96000, 22)
    assert y.sum() == 2852
    assert X.columns.tolist() == MANIFEST["columnas_predictoras_ordenadas"]


@pytest.fixture
def archivo_dataset(request):
    dataset = request.config.getoption("--sidi-dataset")
    if not dataset:
        pytest.skip("Opcional: --sidi-dataset /ruta/dataset_entrenamiento_eps_96000.csv")
    return dataset


def test_rechaza_archivo_modificado_antes_de_entrenar(tmp_path):
    bad = tmp_path / "dataset_falso.csv"
    bad.write_text("label\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        load_verified_dataset(bad, MANIFEST)


def test_cuatro_modelos_con_pipelines_independientes():
    for name in CONFIG["model_names"]:
        p1 = build_pipeline(name, pd.Series([0, 0, 1]), 42)
        p2 = build_pipeline(name, pd.Series([0, 0, 1]), 42)
        assert p1 is not p2
        assert p1.named_steps["scaler"] is not p2.named_steps["scaler"]
        assert p1.named_steps["classifier"] is not p2.named_steps["classifier"]
