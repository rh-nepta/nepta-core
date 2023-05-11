test:
	pip install .
	pytest

pip:
	python3 setup.py sdist

code-style:
	unify -r -i ./
	black -l 120 -S ./
	flake8 nepta unittests

clean:
	# remove all python cache files
	rm -rvf dist nepta_core.egg-info .tox .mypy_cache/ build/
	find . -type f -name "*.pyc" -exec rm -f {} \;
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rvf {} \;


