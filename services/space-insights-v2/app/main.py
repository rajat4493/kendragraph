from fastapi import FastAPI
from app.schemas import Features, Prediction, Context, AugmentedResponse
from app.engine.insights import make_insight
from app.engine.whynot import make_why_not

app = FastAPI(title="Space Insights V2", version="0.2.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/conjunctions/insight", response_model=AugmentedResponse)
def build_insight(features: Features, prediction: Prediction, context: Context):
    insight = make_insight(features, prediction, context)
    why_not = make_why_not(features, prediction, context)
    return AugmentedResponse(
        features=features,
        prediction=prediction,
        context=context,
        insight=insight,
        why_not=why_not
    )
