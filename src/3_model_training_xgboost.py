import os
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from src.config import settings
from src.utils.logger_setup import setup_logger
# Se activa el log automáticamente
setup_logger("model_training_xgboost")

# Importamos el módulo de preprocesamiento construido en la etapa anterior
# Si tu archivo tiene otro nombre, ajusta esta línea
from importlib import import_module
prep = import_module("2_model_preprocessing")

def train_and_evaluate():
    print("======================================================")
    print(" INICIANDO ENTRENAMIENTO DE IA (XGBOOST) PARA EPS")
    print("======================================================")
    
    # 1. Cargar tensores preprocesados (Train/Test Split)
    X_train_scaled, X_test_scaled, y_train, y_test, feature_names = prep.extract_and_preprocess()
    
    # 2. Ingeniería de Hiperparámetros (Manejo de Desbalance)
    # Calculamos la proporción entre consumos normales (0) e irregulares (1)
    # Esto evita el problema de "Accuracy Paradox" en detección de fraudes
    negativos = len(y_train[y_train == 0])
    positivos = len(y_train[y_train == 1])
    ratio_desbalance = negativos / positivos if positivos > 0 else 1
    
    print(f"\n[INFO] Ratio de desbalance calculado: {ratio_desbalance:.2f}")
    
    # Instanciamos el modelo de Árboles Potenciados
    model = XGBClassifier(
        n_estimators=200,             # Número de árboles de decisión
        learning_rate=0.05,           # Tasa de aprendizaje
        max_depth=6,                  # Profundidad máxima para capturar interacciones complejas
        scale_pos_weight=ratio_desbalance, # Penalización a favor de la clase Fraude
        objective='binary:logistic',  # Salida probabilística (Score de Riesgo 0 a 1)
        eval_metric='aucpr',          # Área bajo la curva Precision-Recall
        random_state=42
    )
    
    # 3. Entrenamiento del Modelo (Fit)
    print("[INFO] Entrenando el algoritmo matemático. Por favor espere...")
    model.fit(X_train_scaled, y_train)
    
    # 4. Inferencia en el Set de Prueba (Test)
    print("[INFO] Realizando inferencia sobre datos nunca antes vistos...")
    y_pred = model.predict(X_test_scaled)
    
    print("\n=================== MATRIZ DE CONFUSIÓN ==================")
    cm = confusion_matrix(y_test, y_pred)
    
    # Extraemos los valores aplanando la matriz 2x2
    tn, fp, fn, tp = cm.ravel() 
    
    print(f"[{tn}] Verdaderos Negativos (Lectura normal, IA dijo normal)")
    print(f"[{fp}] Falsos Positivos     (Alarma de revisión técnica errónea)")
    print(f"[{fn}] Falsos Negativos     (Fraude que evadió al algoritmo)")
    print(f"[{tp}] Verdaderos Positivos (FRAUDE DETECTADO EXITOSAMENTE)")
    
    # 6. Serialización (Model Packaging) para el Microservicio FastAPI
    ruta_modelo = os.path.join(settings.PROJECT_ROOT, "models", "xgboost_fraud_model.pkl")
    joblib.dump(model, ruta_modelo)
    print(f"\n[ÉXITO] Modelo de IA entrenado y empaquetado como '{ruta_modelo}'.")
    print("======================================================")

if __name__ == "__main__":
    train_and_evaluate()
