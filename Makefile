.PHONY: install dev-backend dev-frontend test lint build docker-up docker-down

install:
	cd backend && uv sync --extra dev
	npm ci

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

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
