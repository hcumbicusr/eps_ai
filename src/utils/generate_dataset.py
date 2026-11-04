import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from src.config import settings  # Importamos la configuración centralizada

# Configuración
NUM_REGISTROS = 96000
PCT_FRAUDE = 0.03  # 3% de irregularidades
np.random.seed(42)

def generar_dataset():
    print("Generando dataset sintético realista para EPS...")
    
    # 1. Variables base
    fechas = [datetime(2025, 1, 1) + timedelta(days=np.random.randint(0, 365)) for _ in range(NUM_REGISTROS)]
    labels = np.random.choice([0, 1], size=NUM_REGISTROS, p=[1-PCT_FRAUDE, PCT_FRAUDE])
    
    # 2. Construcción del DataFrame
    df = pd.DataFrame({
        'cliente_id': [f"C{str(i).zfill(5)}" for i in range(NUM_REGISTROS)],
        'timestamp_medicion': fechas,
        'label': labels
    })
    
    # 3. Variables de tiempo y estacionalidad
    df['mes_escalar'] = df['timestamp_medicion'].dt.month
    df['contexto_estacional'] = df['mes_escalar'] % 4
    df['es_fin_de_semana'] = df['timestamp_medicion'].dt.weekday.apply(lambda x: 1 if x >= 5 else 0)
    df['es_mes_festivo'] = df['mes_escalar'].apply(lambda x: 1 if x in [7, 12] else 0)
    
    # 4. Perfil del cliente
    df['clase_servicio'] = np.random.choice([0, 1, 2], size=NUM_REGISTROS, p=[0.7, 0.2, 0.1])
    df['categoria_tarifaria'] = np.random.choice([1, 2, 3], size=NUM_REGISTROS)
    df['antiguedad_medidor_meses'] = np.random.randint(1, 120, size=NUM_REGISTROS)
    df['cluster_eps_id'] = np.random.randint(1, 5, size=NUM_REGISTROS)
    df['perfil_cluster_kmeans'] = np.random.randint(0, 4, size=NUM_REGISTROS)
    df['sector_riesgo_0_1'] = np.random.uniform(0, 1, size=NUM_REGISTROS)
    
    # 5. Histórico de consumo (Base normal)
    df['avg_consumo_6m'] = np.random.uniform(10, 40, size=NUM_REGISTROS)
    df['std_consumo_6m'] = df['avg_consumo_6m'] * np.random.uniform(0.05, 0.2, size=NUM_REGISTROS)
    
    # Lógica de consumo actual: Si es fraude, alteramos el consumo artificialmente
    # pero agregamos ruido para que no sea una regla matemática perfecta
    consumos = []
    para_fraudes = np.random.uniform(0.1, 0.9, size=NUM_REGISTROS) # Factor de alteración
    
    for i in range(NUM_REGISTROS):
        base = np.random.normal(df.loc[i, 'avg_consumo_6m'], df.loc[i, 'std_consumo_6m'])
        if df.loc[i, 'label'] == 1:
            # Fraude: Consumo inusualmente bajo (bypass) o picos raros
            if np.random.random() > 0.5:
                consumos.append(max(0, base * para_fraudes[i]))
            else:
                consumos.append(base * (1 + para_fraudes[i] * 2))
        else:
            # Normal: Consumo habitual con algunas variaciones naturales
            consumos.append(max(0, base))
            
    df['consumo_m3'] = [round(c, 2) for c in consumos]
    
    # 6. Variables derivadas
    df['dias_entre_lecturas'] = np.random.randint(28, 33, size=NUM_REGISTROS)
    df['var_pct_mes'] = ((df['consumo_m3'] - df['avg_consumo_6m']) / df['avg_consumo_6m']).round(2)
    df['ceros_ult12'] = np.random.choice([0, 1, 2], size=NUM_REGISTROS, p=[0.9, 0.08, 0.02])
    
    # 7. Operativas y Clima (Desvinculadas de la etiqueta para evitar Leakage)
    df['lectura_estimada_flag'] = np.random.choice([0, 1], size=NUM_REGISTROS, p=[0.95, 0.05])
    df['clave_lectura_tipo'] = np.random.choice([0, 1, 2], size=NUM_REGISTROS, p=[0.8, 0.1, 0.1])
    df['mora_dias'] = np.random.choice([0, 30, 60, 90], size=NUM_REGISTROS, p=[0.7, 0.15, 0.1, 0.05])
    df['tiene_deuda_activa'] = df['mora_dias'].apply(lambda x: 1 if x > 0 else 0)
    df['temperatura_maxima'] = np.random.uniform(20, 35, size=NUM_REGISTROS).round(1)
    df['precipitacion_acumulada'] = np.random.uniform(0, 10, size=NUM_REGISTROS).round(1)
    
    # 8. Reclamos (Para variables a excluir después)
    df['tiene_reclamo'] = df['label'].apply(lambda x: np.random.choice([0, 1], p=[0.6, 0.4]) if x == 1 else np.random.choice([0, 1], p=[0.9, 0.1]))
    df['reclamo_favor_cliente'] = df['tiene_reclamo'].apply(lambda x: 1 if x == 1 and np.random.random() > 0.5 else 0)

    # Ordenar columnas como las espera tu API
    columnas_finales = [
        'cliente_id', 'timestamp_medicion', 'mes_escalar', 'contexto_estacional', 
        'es_fin_de_semana', 'es_mes_festivo', 'clase_servicio', 'categoria_tarifaria', 
        'consumo_m3', 'dias_entre_lecturas', 'lectura_estimada_flag', 'clave_lectura_tipo', 
        'antiguedad_medidor_meses', 'mora_dias', 'tiene_deuda_activa', 'avg_consumo_6m', 
        'std_consumo_6m', 'var_pct_mes', 'ceros_ult12', 'temperatura_maxima', 
        'precipitacion_acumulada', 'sector_riesgo_0_1', 'cluster_eps_id', 
        'perfil_cluster_kmeans', 'tiene_reclamo', 'reclamo_favor_cliente', 'label'
    ]
    df = df[columnas_finales]
    
    # Exportar
    ruta_salida = settings.PATH_DATASET
    df.to_csv(ruta_salida, index=False)
    print(f"Dataset generado exitosamente en: {ruta_salida}")
    print("Muestra de correlación con Fraude (Evitando métricas 1.0 perfectas):")
    print(df.corr(numeric_only=True)['label'].sort_values(ascending=False).head(5))

if __name__ == "__main__":
    generar_dataset()