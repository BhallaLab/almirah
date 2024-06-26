0.5.1 (2024-06-24)
==================

Bugfixes
--------

- Changed specification path building to use kwargs over dict


Improved Documentation
----------------------

- Fixed typos and broken links in docs


0.5.0 (2024-06-12)
==================

Features
--------

- Ability to skip entries while indexing a Layout
- Added new organization rule: pad
- Added reflection of views to Database


Bugfixes
--------

- Fixed file convertion routines broken in release 0.3.0
- Multiple bug fixes in Database: Column types conversion, token retrieval in *request* mode, column querying


0.4.0 (2024-05-16)
==================

Features
--------

- Ability to move Layouts for easy sharing of index
- Ability to read from Google sheets
- Added *request mode* to Database for URL endpoints that can return data
- Support for *Date* type added to mapping config


Bugfixes
--------

- Updated broken tutorial import (`#1 <https://github.com/bhallalab/almirah/issues/1>`__)
- Multiple bug fixes on Indexing, reading YAMLs, DB reflection, DB record retrieval, Layout cloning, and Layout querying


Misc
----

- `#2 <https://github.com/bhallalab/almirah/issues/2>`__


0.3.0 (2024-04-23)
==================

Features
--------

- Generalized Dataset functionality with Components
- Uniqueness-ensured models for consistency


Deprecations and Removals
-------------------------

- Removed support for reporting


Misc
----

- Codebase refactored for improved performance and maintainability


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
