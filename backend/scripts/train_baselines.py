import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import mlflow
import mlflow.sklearn
from sklearn.ensemble import IsolationForest, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, 
    average_precision_score, confusion_matrix, brier_score_loss
)
from sklearn.calibration import calibration_curve
import json
import warnings
warnings.filterwarnings("ignore")

# --- 1. Dataset Generation ---
def generate_synthetic_data(num_devices=10, days=14, interval_min=10):
    np.random.seed(42)
    start_time = datetime(2026, 9, 1)
    points = int(days * 24 * 60 / interval_min)
    
    data = []
    
    for dev_id in range(num_devices):
        base_cpu = np.random.uniform(20, 40)
        base_latency = np.random.uniform(5, 15)
        
        cpu = np.random.normal(base_cpu, 2, points)
        latency = np.random.normal(base_latency, 1, points)
        
        # Inject anomalies
        anomaly_labels = np.zeros(points)
        failure_labels = np.zeros(points)
        
        # Inject 3 random anomalies per device
        for _ in range(3):
            idx = np.random.randint(100, points - 100)
            duration = np.random.randint(3, 10)
            cpu[idx:idx+duration] += np.random.uniform(40, 60) # Spike
            latency[idx:idx+duration] += np.random.uniform(30, 80)
            anomaly_labels[idx:idx+duration] = 1
            
        # Inject 1 failure per device that is preceded by a gradual degradation
        fail_idx = np.random.randint(500, points - 200)
        deg_duration = 36 # 6 hours of degradation
        cpu[fail_idx-deg_duration:fail_idx] += np.linspace(0, 50, deg_duration)
        latency[fail_idx-deg_duration:fail_idx] += np.linspace(0, 100, deg_duration)
        
        # The failure event itself
        failure_labels[fail_idx:fail_idx+6] = 1
        anomaly_labels[fail_idx-deg_duration:fail_idx+6] = 1
        
        df = pd.DataFrame({
            'timestamp': [start_time + timedelta(minutes=interval_min * i) for i in range(points)],
            'device_id': f"dev_{dev_id}",
            'cpu': cpu,
            'latency': latency,
            'is_anomaly': anomaly_labels,
            'is_failure': failure_labels
        })
        data.append(df)
        
    full_df = pd.concat(data).reset_index(drop=True)
    return full_df

# --- 2. Feature Engineering ---
def engineer_features(df):
    df = df.sort_values(by=['device_id', 'timestamp']).reset_index(drop=True)
    
    features = []
    for dev_id, group in df.groupby('device_id'):
        g = group.copy()
        
        # Rolling stats (prevent leakage by using closed='left' or shift)
        for col in ['cpu', 'latency']:
            # 6-step (1 hour) rolling
            g[f'{col}_roll_mean_1h'] = g[col].shift(1).rolling(6, min_periods=1).mean()
            g[f'{col}_roll_std_1h'] = g[col].shift(1).rolling(6, min_periods=1).std().fillna(0)
            
            # Rate of change
            g[f'{col}_roc'] = g[col].shift(1) - g[col].shift(2)
            
            # EWMA
            g[f'{col}_ewma'] = g[col].shift(1).ewm(span=6).mean()
            
            # Z-score based on 24h rolling
            roll_mean_24h = g[col].shift(1).rolling(144, min_periods=1).mean()
            roll_std_24h = g[col].shift(1).rolling(144, min_periods=1).std().fillna(0.1)
            g[f'{col}_zscore'] = (g[col] - roll_mean_24h) / (roll_std_24h + 1e-5)
            
        features.append(g)
        
    return pd.concat(features).reset_index(drop=True).dropna()

# --- 3. Evaluate Model ---
def evaluate(y_true, y_pred, y_prob, name):
    metrics = {
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0),
        'pr_auc': average_precision_score(y_true, y_prob) if y_prob is not None else 0.0,
        'roc_auc': roc_auc_score(y_true, y_prob) if y_prob is not None else 0.0,
        'brier_score': brier_score_loss(y_true, y_prob) if y_prob is not None else 0.0
    }
    
    print(f"\n[{name}] Evaluation:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    print(f"  Confusion Matrix:\n{confusion_matrix(y_true, y_pred)}")
    
    return metrics

# --- 4. Main Pipeline ---
def run():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment("netmind-anomaly-detection")
    
    print("Generating dataset...")
    df = generate_synthetic_data()
    print("Engineering features...")
    df = engineer_features(df)
    
    # Train/Test split chronologically
    split_date = df['timestamp'].max() - pd.Timedelta(days=3)
    train = df[df['timestamp'] < split_date]
    test = df[df['timestamp'] >= split_date]
    
    feature_cols = [c for c in df.columns if c not in ['timestamp', 'device_id', 'is_anomaly', 'is_failure']]
    
    X_train, y_train_anom = train[feature_cols], train['is_anomaly']
    X_test, y_test_anom = test[feature_cols], test['is_anomaly']
    
    print("\n--- ANOMALY DETECTION BASELINES ---")
    
    # 1. Z-Score Anomaly Baseline
    with mlflow.start_run(run_name="Z-Score Threshold"):
        # Predict anomaly if CPU z-score > 3
        y_pred_z = (X_test['cpu_zscore'] > 3).astype(int)
        metrics = evaluate(y_test_anom, y_pred_z, y_pred_z, "Z-Score (Rule-based)")
        mlflow.log_metrics({f"anom_zscore_{k}": v for k, v in metrics.items()})
    
    # 2. Isolation Forest
    with mlflow.start_run(run_name="Isolation Forest"):
        iso = IsolationForest(contamination=0.05, random_state=42)
        iso.fit(X_train)
        
        # Isolation forest returns -1 for anomaly, 1 for normal
        y_pred_iso = (iso.predict(X_test) == -1).astype(int)
        y_score_iso = -iso.score_samples(X_test) # Higher score = more anomalous
        
        metrics = evaluate(y_test_anom, y_pred_iso, y_score_iso, "Isolation Forest")
        mlflow.log_metrics({f"anom_iso_{k}": v for k, v in metrics.items()})
        mlflow.sklearn.log_model(iso, "isolation_forest")
        
    print("\n--- FAILURE PREDICTION BASELINES ---")
    # Formulate prediction: Predict if failure will happen in next 12 hours (72 steps)
    df['future_failure'] = df.groupby('device_id')['is_failure'].transform(
        lambda x: x.shift(-72).rolling(72, min_periods=1).max()
    ).fillna(0)
    
    train = df[df['timestamp'] < split_date]
    test = df[df['timestamp'] >= split_date]
    
    X_train, y_train_fail = train[feature_cols], train['future_failure']
    X_test, y_test_fail = test[feature_cols], test['future_failure']
    
    # 1. Logistic Regression
    with mlflow.start_run(run_name="Logistic Regression"):
        lr = LogisticRegression(max_iter=1000, class_weight='balanced')
        lr.fit(X_train, y_train_fail)
        y_pred_lr = lr.predict(X_test)
        y_prob_lr = lr.predict_proba(X_test)[:, 1]
        
        metrics = evaluate(y_test_fail, y_pred_lr, y_prob_lr, "Logistic Regression")
        mlflow.log_metrics({f"fail_lr_{k}": v for k, v in metrics.items()})
        mlflow.sklearn.log_model(lr, "logistic_regression")
    
    # 2. Random Forest
    with mlflow.start_run(run_name="Random Forest"):
        rf = RandomForestClassifier(n_estimators=50, max_depth=10, class_weight='balanced', random_state=42)
        rf.fit(X_train, y_train_fail)
        y_pred_rf = rf.predict(X_test)
        y_prob_rf = rf.predict_proba(X_test)[:, 1]
        
        metrics = evaluate(y_test_fail, y_pred_rf, y_prob_rf, "Random Forest")
        mlflow.log_metrics({f"fail_rf_{k}": v for k, v in metrics.items()})
        mlflow.sklearn.log_model(rf, "random_forest")
        
    # 3. XGBoost / HistGradientBoosting
    with mlflow.start_run(run_name="LightGBM_Equivalent"):
        xgb = HistGradientBoostingClassifier(max_iter=100, learning_rate=0.1, random_state=42)
        xgb.fit(X_train, y_train_fail)
        y_pred_xgb = xgb.predict(X_test)
        y_prob_xgb = xgb.predict_proba(X_test)[:, 1]
        
        metrics = evaluate(y_test_fail, y_pred_xgb, y_prob_xgb, "HistGradientBoosting")
        mlflow.log_metrics({f"fail_xgb_{k}": v for k, v in metrics.items()})
        mlflow.sklearn.log_model(xgb, "xgboost_baseline")
        
        # Save a sample error analysis report
        fp_mask = (y_test_fail == 0) & (y_pred_xgb == 1)
        fn_mask = (y_test_fail == 1) & (y_pred_xgb == 0)
        report = {
            "false_positives": int(fp_mask.sum()),
            "false_negatives": int(fn_mask.sum()),
            "total_test_samples": len(y_test_fail),
            "difficult_devices": test[fp_mask | fn_mask]['device_id'].value_counts().to_dict()
        }
        with open("error_analysis.json", "w") as f:
            json.dump(report, f, indent=2)
        # mlflow.log_artifact("error_analysis.json")
        
    print("\nExperiment tracking complete. Models logged to MLflow.")

if __name__ == "__main__":
    run()
