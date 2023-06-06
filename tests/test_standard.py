"""Module to test the data.standard.py submodule."""

import os
import yaml
import pytest
import tempfile

from napi.data.standard import Specification


@pytest.fixture
def entities():
    return {"subject": "01", "session": "01", "datatype": "nirs", "suffix": "nirs"}


@pytest.fixture
def spec():
    with open("./tests/configs/specification.yaml") as f:
        config = yaml.load(f, yaml.SafeLoader)
        return Specification("sample", config)


@pytest.fixture
def rules():
    with open("./tests/configs/rules.yaml") as f:
        return yaml.load(f, yaml.SafeLoader)


@pytest.fixture
def dst():
    d = tempfile.TemporaryDirectory()
    yield d
    d.cleanup()


@pytest.fixture
def raw():
    d = tempfile.TemporaryDirectory()
    with open(os.path.join(d.name, "test_001.eeg"), "w") as f:
        f.write("This is a test file.")
    with open(os.path.join(d.name, "sidecar.json"), "w") as f:
        f.write("This is the test file's metadata.")
    yield d
    d.cleanup()


def test_get_valid_entities(spec):
    assert spec.get_valid_entities() == [
        "subject",
        "session",
        "datatype",
        "suffix",
        "extension",
    ]


def test_build_path(spec, entities):
    assert spec.build_path(entities) == "sub-01/ses-01/nirs/sub-01_ses-01_nirs.nirs"


def test_organize(spec, rules, raw, dst):
    rules.update({"source": raw.name, "destination": dst.name})
    spec.organize(rules)
    assert len(os.listdir(raw.name)) == sum([len(f) for _, _, f in os.walk(dst.name)])
