import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, average_precision_score
import joblib

# =====================================================================
# CONFIGURACIÓN DE RUTAS Y LOGGING
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Crear carpeta de logs si no existe
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configurar el archivo de log con fecha y hora
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(LOGS_DIR, f"log_{timestamp}.txt")

class Logger(object):
    """Clase para duplicar la salida de consola en un archivo de texto."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # Necesario para compatibilidad con algunos buffers
        self.terminal.flush()
        self.log.flush()

# Redirigir la salida estándar al logger
sys.stdout = Logger(log_filename)

# Importamos el preprocesador después de definir rutas
from importlib import import_module
prep = import_module("2_model_preprocessing")

# =====================================================================
# FUNCIONES DE EVALUACIÓN Y ENTRENAMIENTO
# =====================================================================

def evaluate_model(model_name, model, X_train, y_train, X_test, y_test):
    print(f"\n======================================================")
    print(f" EVALUANDO MODELO: {model_name}")
    print(f"======================================================")
    
    # 1. Validación Cruzada Estratificada (K-Fold = 5)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    # n_jobs=-1 usa todos los núcleos del procesador
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='f1', n_jobs=-1)
    print(f"[CV] F1-Score Promedio (5-Folds): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    
    # 2. Entrenamiento Final
    model.fit(X_train, y_train)
    
    # 3. Predicciones
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] 
    
    # 4. Métricas Avanzadas
    auc_roc = roc_auc_score(y_test, y_prob)
    auc_pr = average_precision_score(y_test, y_prob)
    print(f"[MÉTRICAS] AUC-ROC: {auc_roc:.4f} | AUC-PR: {auc_pr:.4f}")
    
    # 5. Matriz de Confusión
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    print(f"[MATRIZ] Verdaderos Negativos (OK): {tn} | Falsos Positivos: {fp}")
    print(f"[MATRIZ] Falsos Negativos (Fraude Oculto): {fn} | Verdaderos Positivos: {tp}")
    print("\n" + classification_report(y_test, y_pred, target_names=['Normal (0)', 'Irregular (1)']))
    
    return model

def train_and_evaluate_all():
    print(f"Iniciando Pipeline de IA - {datetime.now()}")
    print(f"Archivo de log generado en: {log_filename}")
    
    print("\nExtrayendo datos y preprocesando tensores...")
    X_train_scaled, X_test_scaled, y_train, y_test, feature_names = prep.extract_and_preprocess()
    
    ratio_desbalance = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
    
    # Definición de modelos
    xgb_model = XGBClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=6,
        scale_pos_weight=ratio_desbalance, objective='binary:logistic', random_state=42
    )
    
    rf_model = RandomForestClassifier(
        n_estimators=150, max_depth=10, class_weight='balanced', random_state=42
    )
    
    svm_model = SVC(
        kernel='rbf', C=1.0, gamma='scale', probability=True, class_weight='balanced', random_state=42
    )
    
    hybrid_model = VotingClassifier(
        estimators=[('xgb', xgb_model), ('rf', rf_model), ('svm', svm_model)],
        voting='soft'
    )
    
    model_registry = {
        "XGBoost": xgb_model,
        "Random Forest": rf_model,
        "SVM (Kernel RBF)": svm_model,
        "Modelo Híbrido (Soft Voting)": hybrid_model
    }
    
    best_model = None
    
    for name, model in model_registry.items():
        trained_model = evaluate_model(name, model, X_train_scaled, y_train, X_test_scaled, y_test)
        if name == "Modelo Híbrido (Soft Voting)":
            best_model = trained_model
            
    # Guardar modelo
    models_dir = os.path.join(PROJECT_ROOT, "models")
    os.makedirs(models_dir, exist_ok=True)
    ruta_modelo = os.path.join(models_dir, "hybrid_fraud_model.pkl")
    
    joblib.dump(best_model, ruta_modelo)
    print(f"\n[SISTEMA] Arquitectura finalizada. Modelo Híbrido empaquetado en '{ruta_modelo}'.")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore')
    try:
        train_and_evaluate_all()
    except Exception as e:
        print(f"\n[ERROR CRÍTICO]: {str(e)}")
    finally:
        print(f"\nProceso terminado. Log cerrado en: {log_filename}")
    