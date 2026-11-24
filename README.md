# Lab 1 — Your First Model Service on Kubernetes

依據 MLOps Foundations & Cloud Native AI 講義實際投影片第 49–52 頁實作。

Repository：https://github.com/ronnie-e2714/ossd_lab1

## 繳交內容與驗證狀態

| 要求 | 檔案 |
| --- | --- |
| scikit-learn 訓練、MLflow params / metrics / model | `train.py` |
| FastAPI 預測與健康檢查 | `app.py` |
| Docker 容器 | `Dockerfile`, `requirements.txt` |
| Kubernetes Deployment + Service | `deployment.yaml` |
| CPU 50%、1–5 replicas 的 HPA | `hpa.yaml` |
| 自動部署、負載、蒐證 | `scripts/`, `.github/workflows/lab.yml` |
| MLflow Run 截圖 | 成功執行後產生 `screenshots/mlflow-run.png` |
| HPA Scaling 截圖 | 成功執行後產生 `screenshots/hpa-scaling.png` |

**截圖存在且 Actions 成功後，才代表完整驗證完成。** 初次上傳時未附虛構執行結果；GitHub Actions 會在真正訓練與 HPA 至少兩個 ready replicas 後，自動提交證據。失敗時請看 Actions 日誌與 `lab1-evidence` artifact，失敗執行的產物僅供診斷。HPA 圖片是原始 `kubectl` 輸出的瀏覽器截圖，保留時間、replicas、CPU 指標與事件；原始文字另存 `evidence/hpa.txt`。

## 執行環境

Python 3.12、Docker Engine（Windows 可用 Docker Desktop Linux containers）、kind、kubectl。安裝套件需能連線 PyPI；建立叢集需能下載容器映像。`scripts/deploy.sh` 在 Bash / WSL / Linux 執行。Windows PowerShell 也可逐行執行下列 Docker 與 kubectl 指令。

```bash
python -m venv .venv
source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
python train.py
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1
```

開啟 http://127.0.0.1:5000，在 `iris` experiment 的 run 查看 `n_estimators=100`、`random_state=42`、`accuracy` 與 `model` artifact。訓練採 80/20 分層切分，輸出 `model.pkl` 和 `evidence/training.json`。模型與本機 MLflow DB 不提交，執行訓練即可重建。訓練與容器使用同一版 scikit-learn，避免模型版本不相容。

另開終端測試 API：

```bash
uvicorn app:app --host 127.0.0.1 --port 8080
curl -X POST http://127.0.0.1:8080/predict -H 'Content-Type: application/json' -d '{"instances":[[5.1,3.5,1.4,0.2]]}'
```

預期回應 `{"predictions":[0]}`（此為預期格式，實際結果以執行證據為準）。每筆輸入依序是 sepal length、sepal width、petal length、petal width，單位 cm；0/1/2 分別為 setosa/versicolor/virginica。不合格輸入回傳 422。

## 部署與 HPA

先停止本機 uvicorn，釋放 8080。全新 lab 叢集可直接執行：

```bash
bash scripts/deploy.sh
kubectl port-forward svc/iris-api 8080:80
```

腳本建立獨立 `mlops` kind 叢集並切換到 `kind-mlops` context，安裝 metrics-server v0.7.2，建置及載入 `iris-api:v1`，套用 Deployment、Service 與 HPA。重跑時若叢集已存在，跳過建立步驟，手動執行後續命令；不要對其他叢集套用作業檔。

kind 的本機 kubelet 憑證需在 metrics-server 加入 `--kubelet-insecure-tls`；此設定僅用於本機 lab。CPU request 為 100m，HPA 50% 是相對於 request 計算，約為每 Pod 50m，不是整台主機 CPU 的 50%。資源與自動擴展機制參考 [Kubernetes HPA 文件](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) 與 [metrics-server 文件](https://github.com/kubernetes-sigs/metrics-server)。

另開兩個終端：

```bash
python scripts/load.py --seconds 300 --concurrency 50
```

```bash
kubectl get hpa iris-api -w
# 另外查看：
kubectl get pods -l app=iris-api
kubectl describe hpa iris-api
kubectl top pods
```

也可使用講義的 hey：

```bash
hey -z 180s -c 50 -m POST -T application/json -d '{"instances":[[5.1,3.5,1.4,0.2]]}' http://localhost:8080/predict
```

`port-forward` 會綁定一個 Pod，足以觸發作業的 HPA 示範，但不等於驗證 Service 的負載平衡。短時間負載未必達到 5 replicas；至少觀察從 1 擴為 2 以上。停止負載後，預設縮容穩定視窗約 5 分鐘。CPU 顯示 `<unknown>` 時先檢查 metrics-server rollout、`kubectl top pods` 及 HPA conditions。

## 自動產生及上傳截圖

推送 main 後，在 Repository → Actions → **Lab 1 execution and evidence** 查看執行。也可按 Run workflow 重跑。流程會跑 API 測試、訓練、kind 部署、真正的 HTTP 負載，以及 Playwright 截圖；成功才 commit 截圖與原始紀錄。若 Repository 禁止 workflow 寫入 contents，需調整 Actions 權限或下載 `lab1-evidence` artifact 後自行提交。

本機也可在 MLflow UI、port-forward、負載均執行中時蒐證：

```bash
pip install playwright==1.51.0
playwright install chromium
python scripts/capture.py
```

最後確認 `screenshots/` 中兩張圖可讀、MLflow 顯示 run 及 accuracy、HPA 顯示至少兩個 ready replicas，並將 Repository 連結交作業。
