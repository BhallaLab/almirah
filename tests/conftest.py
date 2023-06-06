import yaml
import pytest

from napi.data.standard import Specification


@pytest.fixture
def entities():
    return {"subject": "01", "session": "01", "datatype": "nirs"}


@pytest.fixture
def specification():
    with open("./tests/configs/specification.yaml") as f:
        config = yaml.load(f, yaml.SafeLoader)
        return Specification("sample", config)
