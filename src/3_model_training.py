import os
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, average_precision_score
import joblib
from src.config import settings
from src.utils.logger_setup import setup_logger
# Importamos el preprocesador después de definir rutas
from importlib import import_module
import pandas as pd
from sklearn.metrics import f1_score

# Se activa el log automáticamente
setup_logger("model_training")

# prep = import_module("2_model_preprocessing")
prep = import_module("src.2_model_preprocessing")

# =====================================================================
# FUNCIONES DE EVALUACIÓN Y ENTRENAMIENTO
# =====================================================================

def evaluate_model(model_name, model, X_train, y_train, X_test, y_test):
    print(f"\n======================================================")
    print(f" EVALUANDO MODELO: {model_name}")
    print(f"======================================================")
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_metrics = []
    
    # 1. Validación Cruzada Iterativa para evidencias por fold
    for fold, (train_idx, val_idx) in enumerate(cv.split(X_train, y_train), 1):
        X_fold_train, X_fold_val = X_train[train_idx], X_train[val_idx]
        
        # y_train es una Serie de Pandas, usamos iloc
        y_fold_train = y_train.iloc[train_idx]
        y_fold_val = y_train.iloc[val_idx]
        
        model.fit(X_fold_train, y_fold_train)
        y_pred_fold = model.predict(X_fold_val)
        y_prob_fold = model.predict_proba(X_fold_val)[:, 1]
        
        f1 = f1_score(y_fold_val, y_pred_fold)
        pr_auc = average_precision_score(y_fold_val, y_prob_fold)
        tn, fp, fn, tp = confusion_matrix(y_fold_val, y_pred_fold).ravel()
        
        fold_metrics.append({
            "Modelo": model_name, "Fold": fold,
            "F1": round(f1, 4), "PR-AUC": round(pr_auc, 4),
            "VP": tp, "VN": tn, "FP": fp, "FN": fn
        })
        print(f"  -> Fold {fold}: F1={f1:.4f} | PR-AUC={pr_auc:.4f} | Matriz=[VP:{tp} VN:{tn} FP:{fp} FN:{fn}]")

    # 2. Entrenamiento Final sobre todo el dataset de entrenamiento
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    print("\n[REPORTE FINAL SOBRE SET DE PRUEBA (TEST)]")
    print(classification_report(y_test, y_pred, target_names=['Normal (0)', 'Irregular (1)']))
    
    return model, fold_metrics

def train_and_evaluate_all():
    print(f"Iniciando Pipeline de IA - {datetime.now()}")
    X_train_scaled, X_test_scaled, y_train, y_test, feature_names = prep.extract_and_preprocess()
    
    ratio_desbalance = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
    
    xgb_model = XGBClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=6,
        scale_pos_weight=ratio_desbalance, objective='binary:logistic', random_state=42
    )
    rf_model = RandomForestClassifier(n_estimators=150, max_depth=10, class_weight='balanced', random_state=42)
    svm_model = SVC(kernel='rbf', C=1.0, gamma='scale', probability=True, class_weight='balanced', random_state=42)
    hybrid_model = VotingClassifier(estimators=[('xgb', xgb_model), ('rf', rf_model), ('svm', svm_model)], voting='soft')
    
    model_registry = {
        "XGBoost": xgb_model,
        "Random Forest": rf_model,
        "SVM (Kernel RBF)": svm_model,
        "Modelo Hibrido (Soft Voting)": hybrid_model
    }
    
    best_model = None
    all_metrics = []
    
    for name, model in model_registry.items():
        trained_model, metrics = evaluate_model(name, model, X_train_scaled, y_train, X_test_scaled, y_test)
        all_metrics.extend(metrics)
        if name == "Modelo Hibrido (Soft Voting)":
            best_model = trained_model
            
    # Exportar evidencias para el jurado
    logs_dir = os.path.join(settings.PROJECT_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    df_metrics = pd.DataFrame(all_metrics)
    csv_path = os.path.join(logs_dir, "resultados_folds.csv")
    df_metrics.to_csv(csv_path, index=False)
    print(f"\n[SISTEMA] Evidencias exportadas en '{csv_path}'")
    
    models_dir = os.path.join(settings.PROJECT_ROOT, "models")
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(best_model, os.path.join(models_dir, "hybrid_fraud_model.pkl"))
    print(f"[SISTEMA] Modelo Híbrido empaquetado en models/hybrid_fraud_model.pkl")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore')
    try:
        train_and_evaluate_all()
    except Exception as e:
        print(f"\n[ERROR CRÍTICO]: {str(e)}")
    finally:
        print(f"\nProceso terminado. Log cerrado")
    