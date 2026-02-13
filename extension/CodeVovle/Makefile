.PHONY: test test-verbose coverage clean help

help:
	@echo "CodeVovle - Multi-file Code Timeline Tracking CLI"
	@echo ""
	@echo "Available targets:"
	@echo "  test            Run all tests (quiet mode)"
	@echo "  test-verbose    Run all tests with verbose output"
	@echo "  coverage        Run tests with coverage report"
	@echo "  clean           Clean up __pycache__ and .pytest_cache"
	@echo "  help            Show this help message"

test:
	python -m pytest tests/ -q

test-verbose:
	python -m pytest tests/ -v

coverage:
	python -m pytest tests/ --cov=codevovle --cov-report=term-missing

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

.DEFAULT_GOAL := help
