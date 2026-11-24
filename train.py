"""Train Iris, record an MLflow run, and export the serving artifact."""
import argparse
import json
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tracking-uri", default="sqlite:///mlflow.db")
    parser.add_argument("--output", default="model.pkl")
    args = parser.parse_args()
    if args.n_estimators < 1:
        parser.error("--n-estimators must be positive")
    x, y = load_iris(return_X_y=True)
    xtr, xte, ytr, yte = train_test_split(
        x, y, test_size=0.2, random_state=args.seed, stratify=y
    )
    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment("iris")
    with mlflow.start_run(run_name="iris-random-forest") as run:
        params = dict(n_estimators=args.n_estimators, random_state=args.seed, n_jobs=1)
        model = RandomForestClassifier(**params).fit(xtr, ytr)
        accuracy = float(model.score(xte, yte))
        mlflow.log_params({**params, "test_size": 0.2})
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(
            model, artifact_path="model", input_example=xtr[:2],
            signature=infer_signature(xtr, model.predict(xtr)),
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, output)
        result = dict(run_id=run.info.run_id, accuracy=accuracy, params=params,
                      train_samples=len(xtr), test_samples=len(xte))
        Path("evidence").mkdir(exist_ok=True)
        Path("evidence/training.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
