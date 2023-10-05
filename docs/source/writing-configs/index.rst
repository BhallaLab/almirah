Writing configs
===============

.. toctree::
   :hidden:

   specification
   rules
   mapping

napi needs a helping hand from files called configs for certain
tasks. These config files customize napi's workflow for your dataset
needs by setting the knobs and switches of napi as they suit
you. Config files for napi are written in `YAML
<https://yaml.org/spec/1.2.2/>`_. Please see https://yaml.org/ for how
to write YAML.

The :doc:`specification` describes the Specification, a comprehensive
set of rules on how data should be organized.

The :doc:`rules` provides a set of instructions that guide napi as it
attempts to organize and arrange a dataset.

The :doc:`mapping` supplies the mapping from one schema to another to
assist in migration of records from one SQL database to another.
