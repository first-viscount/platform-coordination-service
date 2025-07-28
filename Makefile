.PHONY: help install install-dev format lint test run clean

# Variables
PYTHON := python3.13
PIP := $(PYTHON) -m pip
PORT := 8000

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Platform Coordination Service$(NC)"
	@echo "$(YELLOW)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

format: ## Format code with black and ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	black src tests
	ruff check --fix src tests

lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(NC)"
	ruff check src tests
	black --check src tests

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	pytest

run: ## Run the service locally
	@echo "$(GREEN)Starting service on port $(PORT)...$(NC)"
	uvicorn src.main:app --reload --host 0.0.0.0 --port $(PORT)

clean: ## Clean up generated files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage .pytest_cache
	rm -rf build dist *.egg-info

# Default target
.DEFAULT_GOAL := help