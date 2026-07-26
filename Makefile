.PHONY: dev backend frontend install test lint docker-up docker-down clean

dev:
	@echo "Starting backend + frontend..."
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload &
	cd frontend && npm run dev

backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload

frontend:
	cd frontend && npm run dev

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

test:
	cd backend && python -m pytest -v

lint:
	cd backend && ruff check .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find backend -name '__pycache__' -type d -exec rm -rf {} +
	rm -rf frontend/dist frontend/node_modules/.vite
