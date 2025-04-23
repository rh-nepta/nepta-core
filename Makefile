all:

build-container:
	podman build . -t nepta-env

push-container: build-container
	podman push nepta-env images.paas.redhat.com/perfqe/nepta-env

test:
	hatch run test

build:
	hatch build

fmt:
	hatch run lint:fmt

code-style-check:
	hatch run lint:style

clean:
	# remove all python cache files
	rm -rvf dist nepta_core.egg-info .tox .mypy_cache/ build/
	find . -type f -name "*.pyc" -exec rm -f {} \;
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rvf {} \;


