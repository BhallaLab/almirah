"""Module to test the data.standard.py submodule."""


def test_get_valid_entities(specification):
    assert specification.get_valid_entities() == [
        "subject",
        "session",
        "datatype",
        "suffix",
        "extension",
    ]


def test_build_path(spec, entities):
    assert spec.build_path(entities) == "sub-01/ses-01/nirs/sub-01_ses-01_nirs.nirs"
