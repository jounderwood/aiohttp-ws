import pytest


@pytest.fixture(autouse=True)
def teardown():
    yield
    # print('teardown')
