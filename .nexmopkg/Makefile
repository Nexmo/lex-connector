SHELL := /bin/bash

all:
	$(error Please select a target: deb, rpm, python, gem)

deb:
	nexmo-packaging-build-deb

rpm:
	nexmo-packaging-build-rpm

python:
	nexmo-packaging-build-py

gem:
	nexmo-packaging-build-gem

clean:
	rm -rf build && mkdir build

