"""Exercise the actual training entry point and reload both model artifacts."""
import json
from pathlib import Path
import subprocess
import sys

import joblib
import mlflow.sklearn
from mlflow import MlflowClient
import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split


def test_training_records_and_reloadable_models(tmp_path):
    script = Path(__file__).resolve().parents[1] / "train.py"
    subprocess.run([sys.executable, str(script)], cwd=tmp_path, check=True)
    summary = json.loads((tmp_path / "evidence/training.json").read_text())
    client = MlflowClient(tracking_uri="sqlite:///" + (tmp_path / "mlflow.db").as_posix())
    run = client.get_run(summary["run_id"])
    assert run.info.status == "FINISHED"
    assert run.data.params["n_estimators"] == "100"
    assert run.data.params["test_size"] == "0.2"
    assert run.data.metrics["accuracy"] == summary["accuracy"]
    assert summary["train_samples"] == 120 and summary["test_samples"] == 30
    local_model = joblib.load(tmp_path / "model.pkl")
    artifact_path = client.download_artifacts(run.info.run_id, "model")
    tracked_model = mlflow.sklearn.load_model(artifact_path)
    x, y = load_iris(return_X_y=True)
    _, xtest, _, ytest = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)
    np.testing.assert_array_equal(local_model.predict(x), tracked_model.predict(x))
    assert local_model.score(xtest, ytest) == summary["accuracy"]
