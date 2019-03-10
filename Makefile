PROJECT = aiows

PYTHON_VERSION = 3.6
REQUIREMENTS = requirements.txt
REQUIREMENTS_TEST = requirements-test.txt
VIRTUAL_ENV := .venv$(PYTHON_VERSION)
PYTHON := $(VIRTUAL_ENV)/bin/python
PIP_CONF = pip.conf
PYPI = dev
TEST_SETTINGS = settings_test


tests: venv
	$(VIRTUAL_ENV)/bin/py.test

tests_coverage: venv
	$(VIRTUAL_ENV)/bin/py.test --cov-report html:.reports/coverage --cov-config .coveragerc --cov-report term:skip-covered --cov $(PROJECT)

venv_init:
	if [ ! -d $(VIRTUAL_ENV) ]; then \
		virtualenv -p python$(PYTHON_VERSION) --prompt="($(PROJECT)) " $(VIRTUAL_ENV); \
	fi

venv:  venv_init
	cp $(PIP_CONF) $(VIRTUAL_ENV)/
	$(VIRTUAL_ENV)/bin/pip install -r $(REQUIREMENTS)
	$(VIRTUAL_ENV)/bin/pip install -r $(REQUIREMENTS_TEST)
	ln -sf $(VIRTUAL_ENV)/bin/activate activate


clean_venv:
	rm -rf $(VIRTUAL_ENV)

clean_pyc:
	find . -name \*.pyc -delete

clean: clean_venv clean_pyc

package:
	$(PYTHON) setup.py sdist

pkg_upload:
	$(PYTHON) setup.py sdist upload -r $(PYPI)

pkg_register:
	$(PYTHON) setup.py sdist register -r $(PYPI)
