.PHONY: dev migrate seed test install clean

dev:
	docker-compose up --build

dev-backend:
	cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm install && npm run dev

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python -m app.utils.seed_data

seed-local:
	cd backend && python -m app.utils.seed_data

test:
	docker-compose exec backend pytest tests/ -v

test-local:
	cd backend && pytest tests/ -v

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

setup:
	@echo "Setting up DualTrust AI..."
	cp -n .env.example .env || true
	@echo "✅ Copied .env.example to .env — fill in your API keys!"
	mkdir -p backend/storage/documents

clean:
	docker-compose down -v
	rm -rf backend/storage/documents/*
	rm -rf frontend/node_modules
	find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

logs:
	docker-compose logs -f backend

logs-worker:
	docker-compose logs -f worker
