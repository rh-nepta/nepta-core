test:
	pytest-3 

pip:
	python3 setup.py sdist

clean:
	# remove all python cache files
	find . -type f -name "*.pyc" -exec rm -f {} \;
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rvf {} \;
	rm -rvf dist nepta_core.egg-info


