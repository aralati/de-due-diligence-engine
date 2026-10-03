.PHONY: setup fmt lint test ci

setup:
	pip install -e ".[dev]"
	pre-commit install

fmt:
	ruff format .
	ruff check --fix .

lint:
	ruff check .
	mypy core/

test:
	pytest tests/ -v

ci: fmt lint test
	@echo "Lokal CI simülasyonu tamamlandı — push etmeye hazır."
