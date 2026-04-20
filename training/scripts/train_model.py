from datetime import UTC, datetime
from pathlib import Path

import mlflow
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from xgboost import XGBClassifier

from app.core.config import get_settings
from app.ml.model_bundle import TrainedModelBundle
from training.scripts.generate_synthetic_data import TRAINING_DATA_PATH, generate_synthetic_payments

FEATURE_COLUMNS = [
    "channel",
    "amount",
    "tip_amount",
    "retry_count",
    "gateway_code",
    "network_latency_ms",
    "terminal_type",
    "hour_of_day",
    "day_of_week",
    "prior_store_failure_rate",
    "prior_terminal_failure_rate",
    "peak_hour_flag",
    "payment_amount_bucket",
]
NUMERIC_COLUMNS = [
    "amount",
    "tip_amount",
    "retry_count",
    "network_latency_ms",
    "hour_of_day",
    "day_of_week",
    "prior_store_failure_rate",
    "prior_terminal_failure_rate",
    "peak_hour_flag",
]
CATEGORICAL_COLUMNS = ["channel", "gateway_code", "terminal_type", "payment_amount_bucket"]


def load_training_frame() -> pd.DataFrame:
    if TRAINING_DATA_PATH.exists():
        return pd.read_csv(TRAINING_DATA_PATH)
    return generate_synthetic_payments()


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
            ("numeric", "passthrough", NUMERIC_COLUMNS),
        ]
    )


def train() -> Path:
    settings = get_settings()
    frame = load_training_frame()
    X = frame[FEATURE_COLUMNS]
    y_risk = frame["label_failure"]
    label_encoder = LabelEncoder()
    y_failure = label_encoder.fit_transform(frame["label_failure_class"])

    X_train, X_test, y_risk_train, y_risk_test, y_failure_train, y_failure_test = train_test_split(
        X,
        y_risk,
        y_failure,
        test_size=0.2,
        random_state=42,
        stratify=y_risk,
    )

    preprocessor = build_preprocessor()
    risk_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=120,
                    max_depth=4,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="binary:logistic",
                    eval_metric="logloss",
                ),
            ),
        ]
    )
    failure_pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=140,
                    max_depth=4,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="multi:softmax",
                    num_class=len(label_encoder.classes_),
                ),
            ),
        ]
    )

    risk_pipeline.fit(X_train, y_risk_train)
    failure_pipeline.fit(X_train, y_failure_train)

    risk_probs = risk_pipeline.predict_proba(X_test)[:, 1]
    risk_preds = (risk_probs >= 0.5).astype(int)
    failure_preds = failure_pipeline.predict(X_test)
    metrics = {
        "risk_auc": roc_auc_score(y_risk_test, risk_probs),
        "risk_f1": f1_score(y_risk_test, risk_preds),
        "failure_accuracy": accuracy_score(y_failure_test, failure_preds),
        "failure_weighted_f1": f1_score(y_failure_test, failure_preds, average="weighted"),
    }

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("payment-failure-intelligence")
    model_version = f"trained-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    with mlflow.start_run(run_name=model_version) as run:
        mlflow.log_params(
            {
                "model_type": "xgboost",
                "feature_columns": ",".join(FEATURE_COLUMNS),
                "train_rows": len(X_train),
                "test_rows": len(X_test),
            }
        )
        mlflow.log_metrics(metrics)

        risk_feature_names = (
            risk_pipeline.named_steps["preprocessor"].get_feature_names_out().tolist()
        )
        importances = risk_pipeline.named_steps["classifier"].feature_importances_
        top_features = [
            feature
            for _, feature in sorted(
                zip(importances, risk_feature_names, strict=False), reverse=True
            )[:5]
        ]

        bundle = TrainedModelBundle(
            risk_model=risk_pipeline,
            failure_model=failure_pipeline,
            label_encoder=label_encoder,
            feature_columns=FEATURE_COLUMNS,
            model_version=model_version,
            top_feature_names=top_features,
        )
        bundle.save(settings.model_artifact)
        dump(metrics, settings.model_artifact.parent / "metrics.joblib")
        mlflow.log_artifact(str(settings.model_artifact))
        mlflow.log_artifact(str(settings.model_artifact.parent / "metrics.joblib"))

        try:
            model_uri = f"runs:/{run.info.run_id}/{settings.model_artifact.name}"
            mlflow.register_model(model_uri=model_uri, name=settings.mlflow_model_name)
        except Exception:
            pass

    return settings.model_artifact


if __name__ == "__main__":
    artifact_path = train()
    print(f"Saved trained model bundle to {artifact_path}")

