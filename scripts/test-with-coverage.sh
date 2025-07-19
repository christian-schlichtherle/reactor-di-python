#!/bin/bash
# Run tests with coverage - useful for command line
uv run pytest -c pytest-cov.ini "$@"