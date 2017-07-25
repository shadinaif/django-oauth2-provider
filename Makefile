.DEFAULT_GOAL := test

.PHONY: html_coverage, quality, requirements

html_coverage:
	coverage html && open htmlcov/index.html

requirements:
	pip install -r requirements/requirements.txt

test_requirements:
	pip install -r requirements/requirements.txt
	pip install -r requirements/requirements-test.txt

test:
	tox
