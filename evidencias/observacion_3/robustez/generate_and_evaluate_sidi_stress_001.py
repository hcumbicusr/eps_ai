#!/usr/bin/env python3
"""SIDI-STRESS-001: ex-ante defined synthetic-only robustness check.

No training, no model updates, no use of source CSV values to synthesize outcomes.
Inputs: frozen SIDI-RUN-003 model, SIDI-STRESS-001 config.
Outputs: scenario CSVs, predictions, metrics, integrity report and log.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import (confusion_matrix, f1_score, average_precision_score,
                             precision_score, recall_score, accuracy_score, roc_auc_score)

FIELDS = ["cliente_id","timestamp_medicion","mes_escalar","contexto_estacional","es_fin_de_semana",
          "es_mes_festivo","clase_servicio","categoria_tarifaria","consumo_m3","dias_entre_lecturas",
          "lectura_estimada_flag","clave_lectura_tipo","antiguedad_medidor_meses","mora_dias",
          "tiene_deuda_activa","avg_consumo_6m","std_consumo_6m","var_pct_mes","ceros_ult12",
          "temperatura_maxima","precipitacion_acumulada","sector_riesgo_0_1","cluster_eps_id",
          "perfil_cluster_kmeans","tiene_reclamo","reclamo_favor_cliente","label"]
EXCLUDED = {"cliente_id", "timestamp_medicion", "tiene_reclamo", "reclamo_favor_cliente", "label"}
FEATURES = [f for f in FIELDS if f not in EXCLUDED]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def generate(c, n):
    rng = np.random.default_rng(int(c["seed"]))
    months = rng.integers(1, 13, n)
    years = np.full(n, 2026)
    days = rng.integers(1, 29, n)
    dates = pd.to_datetime({"year":years,"month":months,"day":days})
    positive_count = int(round(n * float(c["positive_share"])))
    y = np.zeros(n, dtype=np.int8)
    y[rng.choice(n, positive_count, replace=False)] = 1
    if c["shift"] == "high_consumption":
        avg = np.clip(rng.lognormal(np.log(37), .45, n), 10, 100)
        std_ratio = rng.uniform(.11, .32, n)
    else:
        avg = np.clip(rng.lognormal(np.log(23), .38, n), 6, 80)
        std_ratio = rng.uniform(.08, .24, n)
    std = avg * std_ratio
    seasonal = 1.0 + (0.10 if c["shift"] == "high_consumption" else 0.06) * np.sin(2*np.pi*months/12)
    base = np.maximum(0, avg * seasonal + rng.normal(0, std))
    cons = base.copy()
    anomalous = y == 1
    pos_idx = np.flatnonzero(anomalous)
    up = rng.random(len(pos_idx)) < .40
    if c["severity"] == "mild":
        fac_down = rng.uniform(.76, .94, len(pos_idx))
        fac_up = rng.uniform(1.08, 1.30, len(pos_idx))
    elif c["severity"] == "moderate":
        fac_down = rng.uniform(.30, .72, len(pos_idx))
        fac_up = rng.uniform(1.45, 2.25, len(pos_idx))
    else: raise ValueError('Unsupported severity')
    cons[pos_idx] = np.maximum(0, cons[pos_idx] * np.where(up, fac_up, fac_down))
    # Naturally varying LEGITIMATE normal consumption; keep label 0 by construction.
    neg_idx = np.flatnonzero(y == 0)
    benign_count = int(round(len(neg_idx) * c["benign_extreme_rate"]))
    benign = rng.choice(neg_idx, size=benign_count, replace=False)
    natural_up = rng.random(benign_count) < .65
    cons[benign] *= np.where(natural_up,
                              rng.uniform(1.45, 2.4, benign_count),
                              rng.uniform(.30, .68, benign_count))
    cons = np.round(np.maximum(0, cons), 2)
    mora = rng.choice([0,30,60,90], n, p=[.68,.17,.10,.05])
    df = pd.DataFrame({
      "cliente_id": [f"STRESS-{c['id']}-{i:05d}" for i in range(n)],
      "timestamp_medicion": dates.dt.strftime('%Y-%m-%d'),
      "mes_escalar": months,
      "contexto_estacional": months % 4,
      "es_fin_de_semana": (dates.dt.dayofweek >= 5).astype(np.int8),
      "es_mes_festivo": np.isin(months,[7,12]).astype(np.int8),
      "clase_servicio": rng.choice([0,1,2],n,p=[.68,.22,.1]),
      "categoria_tarifaria": rng.choice([1,2,3],n,p=[.6,.27,.13]),
      "consumo_m3": cons,
      "dias_entre_lecturas": rng.integers(27,34,n),
      "lectura_estimada_flag": rng.binomial(1,.08,n),
      "clave_lectura_tipo": rng.choice([0,1,2],n,p=[.78,.12,.10]),
      "antiguedad_medidor_meses": rng.integers(1,181,n),
      "mora_dias": mora,
      "tiene_deuda_activa": (mora > 0).astype(np.int8),
      "avg_consumo_6m": avg,
      "std_consumo_6m": std,
      "var_pct_mes": np.round((cons-avg)/avg,2),
      "ceros_ult12": rng.choice([0,1,2,3],n,p=[.86,.10,.03,.01]),
      "temperatura_maxima": np.round(rng.uniform(16,39,n),1),
      "precipitacion_acumulada": np.round(rng.gamma(2,2.3,n),1),
      "sector_riesgo_0_1": rng.beta(2.3,3.4,n),
      "cluster_eps_id": rng.integers(1,6,n),
      "perfil_cluster_kmeans": rng.integers(0,4,n),
      "tiene_reclamo": rng.binomial(1,.11,n),
      "reclamo_favor_cliente": rng.binomial(1,.05,n),
      "label": y
    })
    df = df[FIELDS]
    assert df.shape == (n,27) and df.isna().sum().sum() == 0
    assert int(df['label'].sum()) == positive_count and df['cliente_id'].nunique() == n
    assert np.isfinite(df[FEATURES].to_numpy(dtype=float)).all()
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    if sha(args.model) != cfg['frozen_model_sha256']:
        raise SystemExit('FROZEN MODEL HASH MISMATCH')
    out = args.output; out.mkdir(parents=True,exist_ok=True)
    (out/'config_locked.json').write_bytes(args.config.read_bytes())
    # Independent generator input has no source dataset file, only original model.
    model = joblib.load(args.model)
    assert hasattr(model,'predict_proba')
    model_features = list(model.feature_names_in_) if hasattr(model,'feature_names_in_') else FEATURES
    assert model_features == FEATURES, (model_features,FEATURES)
    all_m=[]; integrity=[]
    for s in cfg['scenarios']:
        data=generate(s,cfg['n_per_scenario'])
        p_data=out/f"dataset_{s['id']}.csv"
        data.to_csv(p_data,index=False)
        # re-read exported file for reproducibility check, data untouched by inference
        data=pd.read_csv(p_data)
        y=data.label.to_numpy()
        prob=model.predict_proba(data[FEATURES])[:,1]
        assert np.isfinite(prob).all() and ((prob >=0)&(prob<=1)).all()
        pred=(prob>=cfg['threshold']).astype(int)
        vn,fp,fn,vp=map(int,confusion_matrix(y,pred,labels=[0,1]).ravel())
        metric={
            'scenario':s['id'],'n':len(data),'positive_n':int(y.sum()),
            'positive_share':float(y.mean()),'F1':float(f1_score(y,pred,zero_division=0)),
            'AP':float(average_precision_score(y,prob)),
            'Precision':float(precision_score(y,pred,zero_division=0)),
            'Recall':float(recall_score(y,pred,zero_division=0)),
            'Accuracy':float(accuracy_score(y,pred)),
            'ROC_AUC':float(roc_auc_score(y,prob)),
            'VN':vn,'FP':fp,'FN':fn,'VP':vp,
            'threshold':cfg['threshold']
        }
        p_pred=out/f"predictions_{s['id']}.csv"
        pd.DataFrame({'cliente_id':data.cliente_id,'label':y,'score':prob,'pred':pred}).to_csv(p_pred,index=False)
        assert sum([vn,fp,fn,vp]) == len(data)
        assert fn+vp == y.sum() and vn+fp == len(y)-sum(y)
        integrity.append({'scenario':s['id'],'data_sha256':sha(p_data),'predictions_sha256':sha(p_pred),
                          'n':len(data),'positive':int(sum(y))})
        all_m.append(metric)
        print(s['id'], 'F1',round(metric['F1'],4),'AP',round(metric['AP'],4),'P',round(metric['Precision'],4),
              'R',round(metric['Recall'],4), 'FP', fp,'FN',fn,flush=True)
    pd.DataFrame(all_m).to_csv(out/'scenario_metrics.csv',index=False)
    (out/'integrity_checks.json').write_text(json.dumps({'model_sha256':sha(args.model),
            'config_sha256':sha(args.config),'scenarios':integrity,'no_training_performed':True},indent=2),encoding='utf-8')
    print('COMPLETED',len(all_m),flush=True)

if __name__ == '__main__': main()
