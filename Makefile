API_PORT ?= 8000
UI_PORT  ?= 8501

run-api:
	uvicorn api.main:app --reload --port $(API_PORT)

run-ui:
	KENDRAGRAPH_API_BASE=http://127.0.0.1:$(API_PORT) \
	streamlit run ui/dashboard.py --server.port $(UI_PORT)

validate:
	python -m backend.validation_engine.cli --days 1
