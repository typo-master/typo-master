.PHONY: help install dev test lint clean run run-docker build-docker

# Default configuration
PYTHON := python
PIP := pip
VENV := venv

help:
	@echo "TypoAgent Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  install       - Install dependencies"
	@echo "  dev           - Install in development mode"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  lint          - Run linting checks"
	@echo "  lint-fix      - Run linting with auto-fix"
	@echo "  clean         - Clean build artifacts"
	@echo "  run           - Run the application"
	@echo "  run-docker    - Run using Docker"
	@echo "  build-docker  - Build Docker image"
	@echo "  format        - Format code with black"

install:
	$(PIP) install -r requirements.txt

dev:
	$(PIP) install -e .
	$(PIP) install pytest pytest-asyncio pytest-cov pytest-mock

test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/ -v --tb=short -m unit

test-integration:
	pytest tests/ -v --tb=short -m integration

test-e2e:
	pytest tests/ -v --tb=short -m e2e

lint:
	flake8 src/ --max-line-length=100 --ignore=E501,W503
	black --check src/ tests/
	mypy src/ --ignore-missing-imports

lint-fix:
	black src/ tests/
	flake8 src/ --max-line-length=100 --ignore=E501,W503 --fix

format:
	black src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".pytest_cache" -delete
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/
	rm -rf logs/* state/* cache/* temp/*

run:
	$(PYTHON) main.py

run-docker:
	docker-compose up

build-docker:
	docker build -t typoagent:latest .

coverage:
	pytest tests/ --cov=src --cov-report=html
	open htmlcov/index.html

docs:
	sphinx-build -b html docs/ docs/_build/html

release:
	python -m build
	twine upload dist/*

# Git hooks
pre-commit:
	black src/ tests/
	flake8 src/ --max-line-length=100 --ignore=E501,W503
	pytest tests/ -m unit -v --tb=short
