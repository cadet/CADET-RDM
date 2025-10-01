# Introduction

Welcome to CADET-Research Data Management, a project by the Forschungszentrum Jülich.

This toolbox aims to help track and version control:

* input data

* code

* software versions

* configurations

* metadata

* output data

and allow for easy sharing, integration, and reproduction of the generated results.


The tools of CADET-RDM can be applied to any project with the structure of an RDM project.


## RDM repository architecture

CADET-RDM projects are structured into two distinct repositories.

1. The **project repository** that contains the input data, code, software and configurations to execute the computations. The output repository is a directory within the project repository.
2. The **output repository** that contains the results of these computations, including all calculations, models and figures created by running the project code. Also stored in the output directory is the metadata used to create the specific result. This includes e.g. the software versions and requirements.

:::{figure} /_static/figures/RDM_wide.png
:width: 700
:alt: RDM structure

CADET-RDM repository architechture
:::

Both the **project** and the **output** repository are their own git repositories. The commit architecture of CADET-RDM allows for easy tracking and reproducing of results and their respective project code.

## RDM commit architecture

Every run of the project code creates a new output branch (*result branch*) in the **output directory**. The repository on this new branch uniquely contains the files created by the execution of the project code. <br> At the same time, for every run of the project code the `run_history` directory on the master branch of the output repository is updated. This directory is unique to the master branch and contains the metadata and software specifications for every branch in the output repository. This directory also links the results in the output branch to the corresponding commit in the project repository used to create them. For transparency and easy accessibility, the most important specifications for every result branch are also documented in the `log.tsv` on the master branch of the output repository.

```{eval-rst}
.. subfigure:: AB
   :gap: 8px
   :subcaptions: below

   .. image:: /_static/figures/RDM-project-commits.png
      :alt: Project Repository
      :width: 300px

   .. image:: /_static/figures/RDM-output-commits.png
      :alt: Output Repository
      :width: 420px

   CADET-RDM commit architechture.
```


Because of this simultanious log of the metadata and the environment used to create a specific output, results can be reproduced easily.

## User function

The tools of CADET-RDM can be used through the command line interface (CLI), via context tracking in Python scripts or within [Jupyter Lab](https://jupyterlab.readthedocs.io/en/latest/).

The following documentation contains an installation guide, a user guide to quickly start using CADET-RDM and more detailed descriptions on using the command line interface, python interface and jupyter interface.