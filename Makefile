.PHONY: help install dev test lint format typecheck build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	pip install .

dev: ## Install with dev dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ --cov=dot_man --cov-report=term-missing

lint: ## Run linting (ruff)
	ruff check dot_man/ tests/

lint-fix: ## Run linting with auto-fix
	ruff check dot_man/ tests/ --fix

format: ## Format code (black)
	black dot_man/ tests/

format-check: ## Check formatting without changes
	black --check dot_man/ tests/

typecheck: ## Run type checking (mypy)
	mypy dot_man/ --ignore-missing-imports

quality: format lint typecheck test ## Run full quality gate (format + lint + typecheck + test)

build: ## Build package
	python -m build

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

all: dev quality ## Install dev + run full quality gate
