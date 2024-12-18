LIB = mikeio1d

check: lint test

build: typecheck test
	python -m build

lint:
	ruff check $(LIB)

format:
	ruff format $(LIB)

test:
	pytest --disable-warnings

typecheck:
	mypy $(LIB)/ --config-file pyproject.toml

# To generate an HTML coverage report, use:    
#     make coverage
# To generate a terminal coverage report, use: 
#     make coverage REPORT=term
coverage:
	@pytest -c .pytest-ci.ini --disable-warnings --cov-report $${REPORT:-html} --cov=$(LIB) tests/

docs: FORCE
	set -e; \
	cd docs; \
	quartodoc build; \
	quartodoc interlinks; \
	quarto render; \
	if [ ! -f _site/index.html ]; then \
        echo "Error: index.html not found. Quarto render failed."; \
        exit 1; \
    fi; \
    cd -

FORCE: