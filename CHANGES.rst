0.2.0 (2024-04-02)
==================

Features
--------

- Ability to hide sensitive columns in db from log.
- Ability to pad tags retrieved during organization.
- More user-friendly log and error messages.
- Replace values in db based on mapping in files.


Bugfixes
--------

- Docs build environment in git updated to prevent empty api reference pages.
- Fixed path building failure due to tag set to None by dict update.
- Fixed path building failure on presence of tags not mentioned in specification.
- Stopped sensitive data leakage by adding anonymization to nirs data conversion.


Improved Documentation
----------------------

- Detailed reference on using the CALM-BRAINS dataset added.
- Pointers included to setup a similar data storage architecture.
- New logo: Yay!!


0.1.0 (2023-12-14)
==================

Features
--------

- BIDS specification support for neuroimaging datasets.
- BIDS-like specification support for genome sequence datasets.
- File format conversion for select neuroimaging data modalities.
- Intefacing with databases supported by SQLAlchemy to insert, retrieve or migrate records.
- Organize unformatted datasets according to a specification.
