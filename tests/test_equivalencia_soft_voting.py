"""Comprueba equivalencia de clasificación probabilística usando data de prueba artificial.
No utiliza dataset SIDI ni el test reservado.
"""
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd
from src.experiments.sidi_run_003 import build_pipeline, probabilities_for_class_one

def test_promedio_scores_equivale_votingclassifier():
    X, y = make_classification(n_samples=400, n_features=22, n_informative=7,
                               weights=[.90,.10],random_state=42)
    X = pd.DataFrame(X)
    y = pd.Series(y)
    tr, te = train_test_split(np.arange(len(y)), test_size=.25, stratify=y, random_state=42)
    models = ["XGBoost", "Random Forest", "SVM (Kernel RBF)"]
    predictions=[]
    for model in models:
        p=build_pipeline(model,y.iloc[tr],42)
        p.fit(X.iloc[tr],y.iloc[tr])
        predictions.append(probabilities_for_class_one(p,X.iloc[te]))
    voter=build_pipeline("Modelo Hibrido (Soft Voting)",y.iloc[tr],42)
    voter.fit(X.iloc[tr],y.iloc[tr])
    voter_probs=probabilities_for_class_one(voter,X.iloc[te])
    np.testing.assert_allclose(np.mean(predictions,axis=0),voter_probs, rtol=0,atol=1e-12)
