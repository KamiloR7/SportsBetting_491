# Project Data

Raw and generated sports datasets are not committed to GitHub.

## NFL Baseline Data

The NFL match prediction baseline uses historical NFL regular-season game data.

The raw NFL dataset should be stored at:

data/raw/nfl_games.csv

The dataset contains historical game information including season, week, game date, home team, away team, home score, and away score.

## Preparing the NFL Dataset

From the project root, run:

python backend/app/ml/features/prepare_nfl_data.py

This script:

- Loads the raw NFL game data
- Keeps completed regular-season games
- Sorts games chronologically
- Calculates historical team features
- Prevents future game results from being used as prediction inputs
- Creates the model-ready dataset

The processed dataset is saved to:

data/processed/nfl_model_data.csv

## Training the NFL Baseline

After preparing the dataset, run:

python backend/app/ml/training/train_nfl_baseline.py

The script trains and evaluates the Logistic Regression baseline model.

## Sprint 1 NFL Baseline Results

- Model-ready games: 6,522
- Training games: 5,217
- Testing games: 1,305
- Correct predictions: 798
- Incorrect predictions: 507
- Accuracy: 61.15%

The model also outputs a predicted winner and home/away win probabilities.

## Data Files

The following files are generated or downloaded locally and are excluded from GitHub:

- data/raw/nfl_games.csv
- data/processed/nfl_model_data.csv

The folder structure remains in GitHub using `.gitkeep` files.