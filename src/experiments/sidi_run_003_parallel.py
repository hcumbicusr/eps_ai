"""Protocolo experimental SIDI-RUN-003 para datos SIDI-DATA-002.

Importante: NO reutiliza ni sobrescribe modelos/ de producción.

Uso desde raíz del repositorio:
    python -m src.experiments.sidi_run_003 --preflight
    python -m src.experiments.sidi_run_003 --execute  # SOLO EN PASO 4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "data/dataset_entrenamiento_eps_96000.csv"
DEFAULT_MANIFEST = PROJECT_ROOT / "protocolos/SIDI_DATA_002_manifest.json"
DEFAULT_CONFIG = PROJECT_ROOT / "protocolos/SIDI_RUN_003_config.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments/run_003"

LOGGER = logging.getLogger("sidi.run_003")


def json_write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_lf(path: Path) -> str:
    """Hash binario normalizando solo finales CRLF a LF; preserva campos."""
    with path.open("rb") as fh:
        content = fh.read()
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def validate_config(config: dict, manifest: dict) -> None:
    if config["dataset_id"] != manifest["dataset_id"]:
        raise ValueError("Dataset ID incongruente entre configuración y manifiesto")
    if not 0 < float(config["test_size"]) < 1:
        raise ValueError("test_size debe pertenecer al intervalo (0,1)")
    if int(config["cv_folds"]) != 5:
        raise ValueError("El protocolo aprobado exige exactamente cinco folds")
    if int(config["positive_class"]) != 1:
        raise ValueError("La etiqueta positiva debe ser 1 (irregular)")
    if float(config["classification_threshold"]) != 0.5:
        raise ValueError("Cambiar el umbral requiere otro protocolo/versionado")
    expected = ["XGBoost", "Random Forest", "SVM (Kernel RBF)", "Modelo Hibrido (Soft Voting)"]
    if config["model_names"] != expected:
        raise ValueError("El conjunto y orden de modelos deben corresponder al protocolo")


def load_verified_dataset(path: Path, manifest: dict) -> tuple[pd.DataFrame, pd.Series]:
    """Verifica integridad del CSV oficial antes de utilizar sus filas."""
    digest = sha256_lf(path)
    expected = manifest["contenido_lf_sha256"]
    if digest != expected:
        raise ValueError(
            f"SHA-256 del dataset no coincide con SIDI-DATA-002: {digest} != {expected}. "
            "No entrenar: documentar y versionar cualquier cambio."
        )
    df = pd.read_csv(path, low_memory=False)
    cols = list(df.columns)
    if cols != manifest["columnas_dataset"]:
        raise ValueError("Orden/nombres de columnas del CSV difieren del manifiesto")
    if len(df) != int(manifest["total_registros"]):
        raise ValueError("Número de registros diferente al manifiesto")
    if not df["cliente_id"].is_unique:
        raise ValueError("Se esperaban 96,000 identificadores sintéticos únicos")
    if df.isna().any().any():
        raise ValueError("El CSV contiene valores faltantes")
    if set(df["label"].unique()) != {0, 1}:
        raise ValueError("El objetivo debe contener únicamente 0 y 1")
    if int((df["label"] == 0).sum()) != int(manifest["clase_0"]):
        raise ValueError("Conteo de clase 0 no coincide con el manifiesto")
    if int((df["label"] == 1).sum()) != int(manifest["clase_1"]):
        raise ValueError("Conteo de clase 1 no coincide con el manifiesto")
    features = manifest["columnas_predictoras_ordenadas"]
    if len(features) != 22 or len(set(features)) != len(features):
        raise ValueError("Se esperaban 22 nombres de características distintos")
    if any(name in manifest["columnas_excluidas"] for name in features):
        raise ValueError("Existe solapamiento entre características y exclusiones")
    X = df.loc[:, features].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Entradas predictoras contienen NaN o infinito")
    y = df["label"].astype(int)
    if X.columns.tolist() != features:
        raise AssertionError("Orden de características no preservado")
    return X.reset_index(drop=True), y.reset_index(drop=True)


def partition_indices(
    y: pd.Series, seed: int, test_size: float, n_folds: int
) -> tuple[np.ndarray, np.ndarray, list[tuple[np.ndarray, np.ndarray]]]:
    row_ids = np.arange(len(y), dtype=np.int64)
    train_ids, test_ids = train_test_split(
        row_ids, test_size=test_size, random_state=seed, stratify=y
    )
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    folds = [
        (train_ids[train_relative], train_ids[val_relative])
        for train_relative, val_relative in cv.split(train_ids, y.iloc[train_ids])
    ]
    # Prevenir cualquier contaminación entre entrenamiento, validación y test.
    assert set(train_ids.tolist()).isdisjoint(test_ids.tolist())
    assert len(train_ids) + len(test_ids) == len(y)
    for fold_train_ids, fold_val_ids in folds:
        assert set(fold_train_ids.tolist()).isdisjoint(fold_val_ids.tolist())
        assert set(fold_val_ids.tolist()).isdisjoint(test_ids.tolist())
        assert set(fold_train_ids.tolist()).union(fold_val_ids.tolist()) == set(train_ids.tolist())
    return train_ids, test_ids, folds


def describe_partition(y: pd.Series, train_ids, test_ids, folds) -> dict:
    def describe(ids):
        labels = y.iloc[ids]
        return {"n": int(len(ids)), "normal": int((labels == 0).sum()),
                "irregular": int((labels == 1).sum())}

    return {
        "dataset": describe(np.arange(len(y))),
        "train": describe(train_ids),
        "test": describe(test_ids),
        "folds": [
            {"fold": i, "fit": describe(ftrain), "validation": describe(fval)}
            for i, (ftrain, fval) in enumerate(folds, start=1)
        ],
    }


def estimator_for(model_name: str, y_fit: pd.Series, seed: int):
    """Modelos frescos; ponderación XGBoost calculada solo con etiquetas del fit."""
    n_pos = int((y_fit == 1).sum())
    n_neg = int((y_fit == 0).sum())
    if n_pos == 0 or n_neg == 0:
        raise ValueError("Subconjunto de entrenamiento sin ambas clases")
    ratio = n_neg / n_pos

    def xgb():
        return XGBClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            scale_pos_weight=ratio,
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            n_jobs=1,
            random_state=seed,
        )

    def rf():
        return RandomForestClassifier(
            n_estimators=150, max_depth=10, class_weight="balanced",
            random_state=seed, n_jobs=1,
        )

    def svm():
        return SVC(
            kernel="rbf", C=1.0, gamma="scale", probability=True,
            class_weight="balanced", random_state=seed,
        )

    mapping = {"XGBoost": xgb, "Random Forest": rf, "SVM (Kernel RBF)": svm}
    if model_name == "Modelo Hibrido (Soft Voting)":
        return VotingClassifier(
            estimators=[("xgb", xgb()), ("rf", rf()), ("svm", svm())],
            voting="soft", n_jobs=1,
        )
    if model_name not in mapping:
        raise ValueError(f"Modelo no reconocido: {model_name}")
    return mapping[model_name]()


def build_pipeline(model_name: str, y_fit: pd.Series, seed: int) -> Pipeline:
    # Se ajusta un StandardScaler completamente nuevo dentro de cada .fit.
    return Pipeline([("scaler", StandardScaler()), ("classifier", estimator_for(model_name, y_fit, seed))])


def probabilities_for_class_one(pipeline: Pipeline, X: pd.DataFrame) -> np.ndarray:
    classes = np.asarray(pipeline.classes_)
    matches = np.flatnonzero(classes == 1)
    if len(matches) != 1:
        raise RuntimeError("El estimador no expone la clase positiva 1")
    return pipeline.predict_proba(X)[:, int(matches[0])]


def metrics(y_true, y_score, threshold: float) -> dict:
    predicted = (np.asarray(y_score) >= threshold).astype(int)
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y_true, predicted, labels=[0, 1]).ravel())
    return {
        "F1": float(f1_score(y_true, predicted, pos_label=1, zero_division=0)),
        "AP": float(average_precision_score(y_true, y_score)),
        "Precision": float(precision_score(y_true, predicted, zero_division=0)),
        "Recall": float(recall_score(y_true, predicted, zero_division=0)),
        "Accuracy": float(accuracy_score(y_true, predicted)),
        "ROC_AUC": float(roc_auc_score(y_true, y_score)),
        "VP": tp, "VN": tn, "FP": fp, "FN": fn,
    }


def rank_models(cv_rows: list[dict], model_names: list[str]) -> list[dict]:
    """Ordena exclusivamente por CV, sin mirar el test ni redondear métricas."""
    grouped = pd.DataFrame(cv_rows).groupby("Modelo", sort=False)
    ranking = []
    for name in model_names:
        frame = grouped.get_group(name)
        ranking.append({
            "Modelo": name,
            "F1_mean": float(frame["F1"].mean()),
            "F1_sd": float(frame["F1"].std(ddof=1)),
            "AP_mean": float(frame["AP"].mean()),
            "AP_sd": float(frame["AP"].std(ddof=1)),
            "Precision_mean": float(frame["Precision"].mean()),
            "Recall_mean": float(frame["Recall"].mean()),
        })
    positions = {name: i for i, name in enumerate(model_names)}
    ranking.sort(key=lambda row: (-row["F1_mean"], -row["AP_mean"], positions[row["Modelo"]]))
    return ranking


def current_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=5, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def environment_metadata() -> dict:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "joblib": joblib.__version__,
        "git_commit_local": current_git_sha(),
    }


def save_splits(path: Path, train_ids, test_ids, folds) -> None:
    arrays = {"train_ids": train_ids, "test_ids": test_ids}
    for i, (fold_train, fold_val) in enumerate(folds, start=1):
        arrays[f"fold_{i}_fit_ids"] = fold_train
        arrays[f"fold_{i}_val_ids"] = fold_val
    np.savez_compressed(path, **arrays)


def configure_run_logger(run_dir: Path) -> None:
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(run_dir / "run.log", encoding="utf-8")):
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)
    LOGGER.propagate = False


def _eval_base_model_fold(model_name, fold_index, fit_ids, val_ids, X, y, seed, threshold, cv_work_dir):
    """Calcula un único clasificador base; guarda los scores para soft vote exacto."""
    import time
    started = time.perf_counter()
    pipeline = build_pipeline(model_name, y.iloc[fit_ids], seed)
    pipeline.fit(X.iloc[fit_ids], y.iloc[fit_ids])
    probs = probabilities_for_class_one(pipeline, X.iloc[val_ids])
    result = {"Modelo": model_name, "Fold": int(fold_index),
              **metrics(y.iloc[val_ids], probs, threshold),
              "N_fit": int(len(fit_ids)), "N_validacion": int(len(val_ids))}
    file_prefix = {"XGBoost":"xgb", "Random Forest":"rf", "SVM (Kernel RBF)":"svm"}[model_name]
    (cv_work_dir / f"{file_prefix}_fold_{fold_index}.npz").parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cv_work_dir / f"{file_prefix}_fold_{fold_index}.npz", probs=probs)
    json_write(cv_work_dir / f"{file_prefix}_fold_{fold_index}.json", {
        "metrics": result, "seconds": time.perf_counter()-started,
        "note": "Las predicciones para Soft Voting se promedian por fold sobre tres modelos base identicos al VotingClassifier"
    })
    return result


def execute_run(config: dict, manifest: dict, dataset_path: Path, output_dir: Path) -> None:
    # Existe una barrera explícita: ejecución solo al invocar --execute.
    if output_dir.exists():
        raise FileExistsError(f"Directorio ya existe; no se sobrescribe ninguna evidencia: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    configure_run_logger(output_dir)
    try:
        LOGGER.info("Inicio %s. Dataset: %s", config["protocol_id"], dataset_path)
        X, y = load_verified_dataset(dataset_path, manifest)
        seed = int(config["random_seed"])
        np.random.seed(seed)
        random.seed(seed)
        train_ids, test_ids, folds = partition_indices(y, seed, float(config["test_size"]), int(config["cv_folds"]))
        save_splits(output_dir / "splits.npz", train_ids, test_ids, folds)
        json_write(output_dir / "partition_summary.json", describe_partition(y, train_ids, test_ids, folds))
        json_write(output_dir / "protocol_config.json", config)
        json_write(output_dir / "dataset_manifest.json", manifest)
        metadata = environment_metadata()
        metadata.update({"dataset_file": str(dataset_path.resolve()),
                         "dataset_sha256_lf_verified": sha256_lf(dataset_path)})
        json_write(output_dir / "environment.json", metadata)
        try:
            installed = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True, text=True, timeout=30, check=True,
            )
            (output_dir / "requirements_freeze.txt").write_text(installed.stdout, encoding="utf-8")
        except (OSError, subprocess.SubprocessError) as exc:
            LOGGER.warning("No se pudo obtener pip freeze: %s", exc)

        # Ejecución computacional en paralelo de folds INDEPENDIENTES.
        # Soft Voting promedia las probabilidades de los tres mismos estimadores
        # base, ajustados individualmente sobre el mismo fold/StandardScaler/seed.
        # Esto es matemáticamente equivalente a VotingClassifier(voting="soft")
        # y evita repetir cinco ajustes internos del SVC probabilístico.
        parallel_config = {"backend": "loky", "n_jobs": 4, "per_fold_checkpoints": True,
                           "reuse_base_fold_scores_for_soft_voting": True,
                           "model_hyperparameters_changed": False,
                           "algorithm_equivalence_test": "tests/test_equivalencia_soft_voting.py"}
        json_write(output_dir / "orchestration_config.json", parallel_config)
        work_dir = output_dir / "cv_checkpoints"
        work_dir.mkdir(exist_ok=False)
        threshold = float(config["classification_threshold"])
        base_names = config["model_names"][:3]
        from joblib import Parallel, delayed
        LOGGER.info("Orquestación computacional paralela de %d modelos base x 5 folds, n_jobs=4",len(base_names))
        tasks = [(name, i, ft, vl) for name in base_names for i, (ft,vl) in enumerate(folds,start=1)]
        base_cv_rows = Parallel(n_jobs=4, backend="loky", batch_size=1)(
            delayed(_eval_base_model_fold)(name,i,ft,vl,X,y,seed,threshold,work_dir)
            for name,i,ft,vl in tasks
        )
        cv_rows = list(base_cv_rows)
        for name in base_names:
            LOGGER.info("CV modelo: %s",name)
            for row in [r for r in base_cv_rows if r["Modelo"]==name]:
                LOGGER.info("  Fold %d: F1=%.4f, AP=%.4f, FP=%d, FN=%d",
                            row["Fold"],row["F1"],row["AP"],row["FP"],row["FN"])

        LOGGER.info("CV modelo: Modelo Hibrido (Soft Voting) | promedio exacto de los 3 scores base")
        for fold_index, (_, val_ids) in enumerate(folds,start=1):
            ps = []
            for base_name in base_names:
                prefix = {"XGBoost":"xgb", "Random Forest":"rf", "SVM (Kernel RBF)":"svm"}[base_name]
                with np.load(work_dir / f"{prefix}_fold_{fold_index}.npz") as pred:
                    ps.append(pred["probs"])
            p_soft = np.mean(np.stack(ps,axis=0),axis=0)
            row = {"Modelo": "Modelo Hibrido (Soft Voting)","Fold":fold_index,
                   **metrics(y.iloc[val_ids],p_soft,threshold),
                   "N_fit": int(len(folds[fold_index-1][0])),"N_validacion":int(len(val_ids))}
            cv_rows.append(row)
            LOGGER.info("  Fold %d: F1=%.4f, AP=%.4f, FP=%d, FN=%d",fold_index,row["F1"],row["AP"],row["FP"],row["FN"])

        pd.DataFrame(cv_rows).to_csv(output_dir / "cv_folds.csv", index=False, float_format="%.10f")
        ranking = rank_models(cv_rows, config["model_names"])
        pd.DataFrame(ranking).to_csv(output_dir / "cv_resumen.csv", index=False, float_format="%.10f")
        selected = ranking[0]["Modelo"]
        json_write(output_dir / "model_selection.json", {
            "selected_model": selected, "criterion": config["selection_rule"],
            "ranked_models": ranking, "test_used_for_selection": False,
        })
        LOGGER.info("Ganador por CV: %s", selected)

        # Ajuste final solo con el 80%% y ÚNICA evaluación del test en este experimento.
        selected_pipeline = build_pipeline(selected, y.iloc[train_ids], seed)
        selected_pipeline.fit(X.iloc[train_ids], y.iloc[train_ids])
        score_test = probabilities_for_class_one(selected_pipeline, X.iloc[test_ids])
        y_test = y.iloc[test_ids]
        results = metrics(y_test, score_test, float(config["classification_threshold"]))
        json_write(output_dir / "test_metrics.json", {
            "model": selected, "test_size": int(len(test_ids)),
            "metrics": results, "positive_label": 1,
            "note": "AP es average_precision_score, no área trapezoidal PR",
        })
        pred_test = (score_test >= float(config["classification_threshold"])).astype(int)
        pd.DataFrame({
            "row_index_original": test_ids, "label_real_sintetico": y_test.to_numpy(),
            "score_irregular": score_test, "prediccion": pred_test,
        }).to_csv(output_dir / "test_predictions.csv", index=False, float_format="%.10f")
        cm = confusion_matrix(y_test, pred_test, labels=[0, 1])
        pd.DataFrame(cm, index=["Real_Normal", "Real_Irregular"],
                     columns=["Pred_Normal", "Pred_Irregular"]).to_csv(output_dir / "test_confusion_matrix.csv")
        json_write(output_dir / "test_classification_report.json", classification_report(
            y_test, pred_test, labels=[0, 1], target_names=["Normal", "Irregular"],
            output_dict=True, zero_division=0,
        ))
        # Sólo un pipeline conjunto, sin sobrescribir el modelo/escalador en models/.
        model_path = output_dir / "selected_pipeline.joblib"
        joblib.dump(selected_pipeline, model_path, compress=3)
        json_write(output_dir / "artifact_manifest.json", {
            "model_path": model_path.name,
            "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
            "model_name": selected,
            "input_columns_ordered": manifest["columnas_predictoras_ordenadas"],
            "inference": "Utilizar predict_proba sobre DataFrame; incluye StandardScaler internamente",
            "not_deployed": True,
        })
        LOGGER.info("FIN. Test F1=%.4f AP=%.4f; artefacto en %s", results["F1"], results["AP"], model_path)
    except Exception:
        LOGGER.exception("La ejecución quedó incompleta. Conservar carpeta para auditoría; no reutilizarla.")
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="SIDI-RUN-003: protocolo experimental con separación CV/test")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true", help="Solo verificar dataset y particiones; NO entrena")
    mode.add_argument("--execute", action="store_true", help="Entrenamiento real (reservado para el Paso 4)")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, help="Ruta opcional del JSON de preflight")
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_config(config, manifest)

    if args.preflight:
        X, y = load_verified_dataset(args.dataset, manifest)
        train_ids, test_ids, folds = partition_indices(
            y, int(config["random_seed"]), float(config["test_size"]), int(config["cv_folds"])
        )
        data = {
            "mode": "preflight_only_no_training", "dataset_id": manifest["dataset_id"],
            "dataset_sha256_lf": sha256_lf(args.dataset),
            "features": X.columns.tolist(),
            "partitions": describe_partition(y, train_ids, test_ids, folds),
            "protocol_id": config["protocol_id"],
            "code_status": "No se ajustaron modelos; no hay nuevas métricas",
        }
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            json_write(args.report, data)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        execute_run(config, manifest, args.dataset, args.output_dir)


if __name__ == "__main__":
    main()
