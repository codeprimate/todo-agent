.PHONY: clean build check publish format lint test-lint all-lint install install-dev

# ==============================================================================
# Build and Publishing
# ==============================================================================

install: build uninstall
	@echo "📦 Installing built package locally..."
	pip install dist/*.whl

install-dev: uninstall
	@echo "🔧 Installing package in development mode with dev dependencies..."
	pip install -e ".[dev]"

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ .eggs/ *.egg-info

build: clean
	@echo "🔨 Building package..."
	python -m build

check:
	@echo "✅ Checking distribution files..."
	twine check dist/*

publish: clean build check
	@echo "🚀 Publishing to PyPI..."
	twine upload dist/* 

uninstall:
	@echo "🧹 Uninstalling package..."
	pip uninstall -y todo-agent

# ==============================================================================
# Linting and Code Quality
# ==============================================================================

format:
	@echo "🎨 Formatting and linting code with Ruff..."
	ruff check --fix todo_agent/ tests/
	ruff format todo_agent/ tests/

lint:
	@echo "🔍 Running Ruff linting..."
	ruff check todo_agent/ tests/
	@echo "🔍 Running MyPy type checking..."
	mypy todo_agent/
	@echo "🔍 Running Bandit security checks..."
	bandit -r todo_agent/ || true

# ==============================================================================
# Testing
# ==============================================================================

test:
	@echo "🧪 Running tests with linting and coverage..."
	pytest --cov=todo_agent --cov-report=term-missing --cov-report=html 