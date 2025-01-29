#!/bin/bash
source /opt/miniconda/bin/activate neuro

exec python /run.py "$@"