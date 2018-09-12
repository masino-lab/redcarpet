redcarpet

The main.py routine executes an information theoretic rollup of an ontology based on the objects annotated by
concepts in the ontology. The rollup method is a greedy inverted depth-first search. Assuming there are N concepts
that directly annotate an object in the input ontology, and M desired annotators (i.e. M < N), The method selects
the concept to eliminate from the current leaves in the ontology by determining which leaf, if removed, will yield
the minimum standard deviation in the information content of each concept that directly annotates an object, noting
that the true path rule applies (i.e. concepts inherit the annotations of their descendant concepts).

==============================

Information theoretic method to roll up ontology concepts annotated to objects

# Project Organization
------------

    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data` or `make train`
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
    │                         the creator's initials, and a short `-` delimited description, e.g.
    │                         `1.0-jqp-initial-data-exploration`.
    │
    ├── rollup             <- source code for use in this project
    │
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
    │                         generated with `pip freeze > requirements.txt`
    │
    ├── tox.ini            <- tox file with settings for running tox; see tox.testrun.org

--------

# Python requirements

The code was developed on Python version 3.6.3

pip3 install -r requirements.txt

# Usage

```python main.py PATH/TO/YOUR/CONFIG/FILE```

Configuration settings in configuration file. See conf/sample.ini for illustration.

## Input files (required):
*FILE_ONTOLOGY*: File detailing the ontology concepts. Each row of this file is of the form:
child_concept_id: parent_1_concept_id, parent_2_concept_id, ...

_OR_

root_node_concept_id

where the parent_#_concept_id are the direct parents of the child only.

NOTE: This file should only include the portion of the ontology that spans the ontology root down to annotating leaves.
That is, a subgraph of the overall ontology where all leaves in the subgraph directly annotate an object.

*FILE_ANNOTATIONS*: File detailing the objects directly annotated by a concept. Each row of this file is of the form:
concept_id: object_id_1, object_id_2, ...

where the object_id_# are identifiers of for the objects annotated by the concept (e.g. a person)

## Output files (optional)
For any output file that is present in the configuration file, the corresponding output will be stored.

*FILE_ROLLUP*: File detailing the concepts to which a given concept was rolled. Each row is of the form:
concept_id: concept_roll_id_1, concept_roll_id_2, ...

where concept_id is the concept that was removed from the ontology subgraph, and the concept_roll_id_# are one or more
concepts to which the concept_id was rolled.

*FILE_ROLLUP_LEVELS*: File detailing the number of edges in the longest path between the concept that was rolled up and
the ancestors it was rolled into.

*FILE_BEST_MEAN_IC*: File containing the mean information content across all direct annotators for each iteration of the
rollup algorithm

*FILE_BEST_STDEV_IC*: File containing the standard deviation of the information content across all direct annotators
for each iteration of the rollup algorithm

*FILE_ONTOLOGY*: File containing the concepts in the rolled up ontology. Same format is Input FILE_ONTOLOGY

*FILE_ANNOTATIONS*: File containing concepts with direct object annotations. Same format as Input FILE_ANNOTATIONS

## Rollup_Options
*TOTAL_ANNOTATORS_AFTER_ROLLUP*: number of direct annotators after rollup

*MAXIMUM_ITERATIONS*: maximum number of iterations for algorithm (note, this typically must be higher than the
difference between the initial and final number of direct annotators as the direct annotator count can grow as leaves
are rolled into multiple parent concepts that were not originally direct annotators)

*PRINT_STATUS_FREQ*: how often to print status in iterations

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
