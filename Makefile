.PHONY: up down seed test frontend backend migrate seed-local test-local migrate-local

up:
	docker compose up --build

down:
	docker compose down -v

seed:
	docker compose up -d postgres
	docker compose run --build --rm backend alembic upgrade head
	docker compose run --build --rm backend python scripts/seed.py

test:
	docker compose run --build --rm backend pytest -q

frontend:
	docker compose up frontend

backend:
	docker compose up backend

migrate:
	docker compose run --build --rm backend alembic upgrade head

seed-local:
	cd backend && python scripts/seed.py

test-local:
	cd backend && python -m pytest -q

migrate-local:
	cd backend && alembic upgrade head
