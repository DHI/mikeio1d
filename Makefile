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
	@pytest --cov-report $${REPORT:-html} --cov=$(LIB) tests/

docs: FORCE
	cd docs && quarto add --no-prompt .
	cd docs && quartodoc build
	cd docs && quartodoc interlinks
	quarto render docs

FORCE: