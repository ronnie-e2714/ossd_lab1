"""Iris inference service. Train model.pkl before starting the service."""
from contextlib import asynccontextmanager
import os
from typing import Annotated

import joblib
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, FiniteFloat


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = joblib.load(os.getenv("MODEL_PATH", "model.pkl"))
    yield


app = FastAPI(title="Lab 1 Iris predictor", lifespan=lifespan)
IrisRow = Annotated[list[FiniteFloat], Field(min_length=4, max_length=4)]


class PredictionRequest(BaseModel):
    instances: Annotated[list[IrisRow], Field(min_length=1, max_length=1024)]


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/predict")
def predict(body: PredictionRequest, request: Request):
    return {"predictions": request.app.state.model.predict(body.instances).tolist()}
