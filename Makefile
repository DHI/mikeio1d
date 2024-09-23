docs: FORCE
	cd docs && quarto add --no-prompt .
	cd docs && quartodoc build
	cd docs && quartodoc interlinks
	quarto render docs

FORCE: