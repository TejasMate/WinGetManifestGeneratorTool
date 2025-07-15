.PHONY: help install install-dev test test-unit test-integration test-e2e lint format type-check clean build docs serve-docs
.DEFAULT_GOAL := help

PYTHON := python
PIP := pip
PACKAGE_NAME := winget_automation

# Colors for output
BOLD := \033[1m
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BOLD)WinGet Manifest Automation Tool$(RESET)"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package for production use
	@echo "$(YELLOW)Installing package...$(RESET)"
	$(PIP) install -e .

install-dev: ## Install the package with development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(RESET)"
	$(PIP) install -e ".[dev]"
	$(PIP) install -r requirements-dev.txt

test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests only
	@echo "$(YELLOW)Running unit tests...$(RESET)"
	$(PYTHON) -m pytest tests/unit/ -v --cov=$(PACKAGE_NAME) --cov-report=term-missing

test-integration: ## Run integration tests only
	@echo "$(YELLOW)Running integration tests...$(RESET)"
	$(PYTHON) -m pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	@echo "$(YELLOW)Running end-to-end tests...$(RESET)"
	$(PYTHON) -m pytest tests/e2e/ -v

test-all: ## Run all tests including slow ones
	@echo "$(YELLOW)Running all tests...$(RESET)"
	$(PYTHON) -m pytest tests/ -v --cov=$(PACKAGE_NAME) --cov-report=term-missing --cov-report=html

lint: ## Run code linting
	@echo "$(YELLOW)Running linters...$(RESET)"
	flake8 src/ tests/ scripts/ examples/
	isort --check-only src/ tests/ scripts/ examples/
	black --check src/ tests/ scripts/ examples/

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(RESET)"
	isort src/ tests/ scripts/ examples/
	black src/ tests/ scripts/ examples/

type-check: ## Run type checking
	@echo "$(YELLOW)Running type checks...$(RESET)"
	mypy src/$(PACKAGE_NAME)

check: lint type-check test-unit ## Run all checks (lint, type-check, unit tests)

clean: ## Clean up build artifacts and cache files
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build the package for distribution
	@echo "$(YELLOW)Building package...$(RESET)"
	$(PYTHON) -m build

docs: ## Generate documentation
	@echo "$(YELLOW)Generating documentation...$(RESET)"
	cd docs && sphinx-build -b html . _build/html

serve-docs: docs ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation at http://localhost:8000$(RESET)"
	cd docs/_build/html && $(PYTHON) -m http.server 8000

dev-setup: install-dev ## Complete development environment setup
	@echo "$(GREEN)Development environment setup complete!$(RESET)"
	@echo "You can now:"
	@echo "  - Run tests with: make test"
	@echo "  - Format code with: make format"

health-check: ## Run system health checks
	@echo "$(YELLOW)Running health checks...$(RESET)"
	$(PYTHON) scripts/test_monitoring.py

config-check: ## Validate configuration
	@echo "$(YELLOW)Checking configuration...$(RESET)"
	$(PYTHON) scripts/test_config.py

demo: ## Run integration demo
	@echo "$(YELLOW)Running integration demo...$(RESET)"
	$(PYTHON) examples/integration_demo.py

pre-commit: format lint type-check test-unit ## Run all pre-commit checks

ci: install-dev check test-all build ## Run full CI pipeline

# Development shortcuts
run-tests: ## Quick test runner
	$(PYTHON) scripts/run_tests.py

# Project information
info: ## Show project information
	@echo "$(BOLD)Project Information$(RESET)"
	@echo "Name: WinGet Manifest Automation Tool"
	@echo "Package: $(PACKAGE_NAME)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Location: $(shell pwd)"

# Workflow execution targets
run-all: ## Run complete workflow (all 3 steps)
	@echo "$(BOLD)$(GREEN)Running complete WinGet workflow...$(RESET)"
	$(PYTHON) get_started.py --all

run-step1: ## Run Step 1: Package Processing
	@echo "$(BOLD)$(BLUE)Running Step 1: Package Processing...$(RESET)"
	$(PYTHON) get_started.py --step 1

run-step2: ## Run Step 2: GitHub Analysis  
	@echo "$(BOLD)$(BLUE)Running Step 2: GitHub Analysis...$(RESET)"
	$(PYTHON) get_started.py --step 2

run-step3: ## Run Step 3: Komac Generation
	@echo "$(BOLD)$(BLUE)Running Step 3: Komac Generation...$(RESET)"
	$(PYTHON) get_started.py --step 3

# Legacy workflow targets  
run-legacy: ## Run traditional sequential workflow
	@echo "$(BOLD)$(YELLOW)Running legacy workflow...$(RESET)"
	cd src && $(PYTHON) PackageProcessor.py
	cd src && $(PYTHON) GitHub.py  
	cd src && $(PYTHON) KomacCommandsGenerator.py

# Individual component targets
run-processor: ## Run PackageProcessor only
	@echo "$(BOLD)$(BLUE)Running PackageProcessor...$(RESET)"
	cd src && $(PYTHON) PackageProcessor.py

run-github: ## Run GitHub analysis only
	@echo "$(BOLD)$(BLUE)Running GitHub analysis...$(RESET)"
	cd src && $(PYTHON) GitHub.py

run-komac: ## Run Komac generation only  
	@echo "$(BOLD)$(BLUE)Running Komac generation...$(RESET)"
	cd src && $(PYTHON) KomacCommandsGenerator.py

# Enhanced filtering targets
test-filter: ## Test enhanced filtering with sample data
	@echo "$(BOLD)$(GREEN)Testing enhanced filtering...$(RESET)"
	cd src/github && $(PYTHON) Filter.py

demo-filter: ## Run filtering demo
	@echo "$(BOLD)$(GREEN)Running filtering demonstration...$(RESET)"
	$(PYTHON) -c "import sys; sys.path.append('src'); from github.Filter import process_filters; process_filters('test_data/test_input.csv', 'test_data/output')"

# Setup and maintenance targets
setup-env: ## Set up environment file
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env file from example...$(RESET)"; \
		cp .env.example .env 2>/dev/null || echo "GITHUB_TOKEN=your_token_here" > .env; \
		echo "$(GREEN)Please edit .env file with your GitHub token$(RESET)"; \
	else \
		echo "$(GREEN).env file already exists$(RESET)"; \
	fi

check-config: ## Verify configuration
	@echo "$(BOLD)$(BLUE)Checking configuration...$(RESET)"
	$(PYTHON) -c "from src.config import get_config; print('✅ Configuration loaded successfully')"

clean-output: ## Clean output directories
	@echo "$(BOLD)$(YELLOW)Cleaning output directories...$(RESET)"
	rm -rf data/github/*.csv data/github/*.txt data/github/*.md
	rm -rf test_data/output/*
	@echo "$(GREEN)Output directories cleaned$(RESET)"
