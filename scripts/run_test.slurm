#!/bin/bash
#SBATCH --job-name=learncom-test
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err
#SBATCH --time=00:30:00
#SBATCH --partition=cpu

python -m pytest -q
