#!/usr/bin/env bash
set -euo pipefail
kind create cluster --name mlops --image kindest/node:v1.32.2 --wait 120s
kubectl config use-context kind-mlops
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
# Local kind certificates are not signed by a publicly trusted CA.
kubectl -n kube-system patch deployment metrics-server --type=json -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
docker build -t iris-api:v1 .
kind load docker-image iris-api:v1 --name mlops
kubectl apply -f deployment.yaml -f hpa.yaml
kubectl rollout status deployment/iris-api --timeout=180s
