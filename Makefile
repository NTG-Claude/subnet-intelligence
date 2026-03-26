.PHONY: score score-dry api frontend test migrate lint

score:
	python -m scorer.run --all-subnets

score-dry:
	python -m scorer.run --dry-run --all-subnets

score-netuid:
	python -m scorer.run --netuid $(NETUID)

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest tests/ -v

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(MSG)"

scheduler:
	python -m scorer.scheduler
