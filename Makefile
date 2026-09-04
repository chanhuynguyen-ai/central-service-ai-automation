.PHONY: install dev-backend dev-frontend db-upgrade db-revision data-quality test lint build docker-up docker-down

install:
	cd backend && uv sync --extra dev
	npm ci

db-upgrade:
	cd backend && uv run alembic upgrade head

db-revision:
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

data-quality:
	python3 scripts/clean_service_requests.py

dev-backend:
	cd backend && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev

test:
	cd backend && uv run pytest
	npm run test

lint:
	cd backend && uv run ruff check app tests
	npm run lint
	npm run typecheck

build:
	npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down
