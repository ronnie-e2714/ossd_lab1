"""Capture MLflow UI and a browser view of unmodified kubectl output."""
import html
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


def kubectl(*args):
    return subprocess.check_output(["kubectl", *args], text=True)


def main():
    folder = Path("screenshots")
    folder.mkdir(exist_ok=True)
    evidence = Path("evidence")
    evidence.mkdir(exist_ok=True)
    history = []
    scaled = False
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        state = json.loads(kubectl("get", "hpa", "iris-api", "-o", "json"))
        deployment = json.loads(kubectl("get", "deployment", "iris-api", "-o", "json"))
        history.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                        "hpa": state["status"], "deployment": deployment["status"]})
        if (state["status"].get("currentReplicas", 0) >= 2
                and deployment["status"].get("readyReplicas", 0) >= 2):
            scaled = True
            break
        time.sleep(10)
    (evidence / "hpa-history.json").write_text(json.dumps(history, indent=2))
    commands = [("get", "hpa", "iris-api"), ("get", "pods", "-l", "app=iris-api"),
                ("describe", "hpa", "iris-api")]
    output = datetime.now(timezone.utc).isoformat() + "\n\n"
    for args in commands:
        output += "$ kubectl " + " ".join(args) + "\n" + kubectl(*args) + "\n"
    (evidence / "hpa.txt").write_text(output)
    run = json.loads((evidence / "training.json").read_text())
    import mlflow
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    experiment_id = mlflow.get_run(run["run_id"]).info.experiment_id
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.goto(f"http://127.0.0.1:5000/#/experiments/{experiment_id}/runs/{run['run_id']}")
        page.get_by_text("accuracy", exact=True).first.wait_for(timeout=60000)
        page.screenshot(path=str(folder / "mlflow-run.png"), full_page=True)
        page.set_content('<meta charset="utf-8"><style>body{background:#101820;color:#e9f0f4;padding:24px}pre{font:17px monospace;white-space:pre-wrap}</style><h1>Actual Kubernetes HPA output</h1><pre>' + html.escape(output) + '</pre>')
        page.screenshot(path=str(folder / "hpa-scaling.png"), full_page=True)
        browser.close()
    if not scaled:
        raise SystemExit("HPA did not reach at least two ready replicas; evidence is diagnostic only")


if __name__ == "__main__":
    main()
