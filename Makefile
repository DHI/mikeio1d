LIB = mikeio1d

docs: FORCE
	set -e; \
	cd docs; \
	uv run quartodoc build; \
	uv run quartodoc interlinks; \
	uv run quarto render; \
	if [ ! -f _site/index.html ]; then \
        echo "Error: index.html not found. Quarto render failed."; \
        exit 1; \
    fi; \
    cd -

FORCE: