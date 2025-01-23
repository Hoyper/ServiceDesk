.PHONY: lint
lint:
	mypy --install-types --non-interactive --config-file setup.cfg .
	flake8 .

.PHONY: format
format:
	black .
	isort .

.PHONY: flint
flint: format lint

.PHONY: migration
migration:
	alembic revision --autogenerate

.PHONY: upgrade
upgrade:
	alembic upgrade head


.PHONY: start
start:
	uvicorn app.api.main:app --reload