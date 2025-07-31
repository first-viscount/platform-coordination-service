.PHONY: help install install-dev format lint test type-check run run-docker clean

# Variables
PYTHON := python
PIP := $(PYTHON) -m pip
PORT := 8000

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Platform Coordination Service$(NC)"
	@echo "$(YELLOW)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

install-dev: install ## Install development dependencies
	@echo "$(YELLOW)Development dependencies included in requirements.txt$(NC)"

format: ## Format code with black and ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	black src tests
	ruff format src tests
	ruff check --fix src tests
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(NC)"
	@ruff check --ignore B008 src tests || (echo "$(RED)✗ Ruff check failed$(NC)" && exit 1)
	@black --check src tests || (echo "$(RED)✗ Black check failed$(NC)" && exit 1)
	@echo "$(GREEN)✓ All linting checks passed$(NC)"

type-check: ## Run mypy type checking
	@echo "$(YELLOW)Running type checks...$(NC)"
	mypy src
	@echo "$(GREEN)✓ Type checks passed$(NC)"

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	PYTHONPATH=src pytest -v tests/
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	PYTHONPATH=src pytest --cov=platform_coordination --cov-report=term-missing tests/

verify: ## Verify service without running server
	@echo "$(YELLOW)Verifying service configuration and endpoints...$(NC)"
	@PYTHONPATH=. python scripts/verify-service.py
	@echo "$(GREEN)✓ Service verification complete$(NC)"

verify-full: ## Run comprehensive verification tests
	@echo "$(YELLOW)Running comprehensive verification...$(NC)"
	@PYTHONPATH=. pytest tests/test_service_verification.py -v
	@PYTHONPATH=. python scripts/verify-service.py
	@echo "$(GREEN)✓ Full verification complete$(NC)"

run: ## Run the service locally
	@echo "$(GREEN)Starting service on port $(PORT)...$(NC)"
	$(PYTHON) -m uvicorn src.main_db:app --reload --host 0.0.0.0 --port $(PORT)

run-docker: ## Run the service in Docker
	@echo "$(GREEN)Starting service in Docker...$(NC)"
	docker-compose up --build

clean: ## Clean up generated files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage .pytest_cache htmlcov
	rm -rf build dist *.egg-info
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# Convenience targets
fmt: format ## Alias for format
check: lint type-check test ## Run all checks (lint, type-check, test)

# Include integration test targets
-include Makefile.integration

# Default target
.DEFAULT_GOAL := help