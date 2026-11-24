import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    x, y = load_iris(return_X_y=True)
    path = tmp_path / "model.pkl"
    joblib.dump(RandomForestClassifier(n_estimators=10, random_state=42).fit(x, y), path)
    monkeypatch.setenv("MODEL_PATH", str(path))
    with TestClient(app) as c:
        yield c


def test_health_and_prediction(client):
    assert client.get("/healthz").json() == {"ok": True}
    response = client.post("/predict", json={"instances": [[5.1, 3.5, 1.4, 0.2]]})
    assert response.status_code == 200
    assert response.json() == {"predictions": [0]}


@pytest.mark.parametrize("instances", [[], [[1, 2, 3]], [[1, 2, 3, 4, 5]], [["NaN", 2, 3, 4]], [[1, 2, 3, 4]] * 1025])
def test_invalid_input(client, instances):
    assert client.post("/predict", json={"instances": instances}).status_code == 422
