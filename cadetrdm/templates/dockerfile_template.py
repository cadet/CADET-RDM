dockerfile_template = """
# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG CONDA_VERSION=24.11.3
FROM condaforge/miniforge3:${CONDA_VERSION}-0 AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /rdm_workdir

USER root

# Prevents interactive prompts during apt-get
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y git git-lfs ssh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY environment.yml /tmp/environment.yml

RUN conda env update -n base --file /tmp/environment.yml
"""
