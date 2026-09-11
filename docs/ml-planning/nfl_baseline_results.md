# NFL Baseline Match Prediction Model

## Model

The Sprint 1 NFL baseline uses Logistic Regression to predict the winner of an NFL regular-season game.

## Dataset

The development dataset contains historical NFL regular-season games from 1999 through 2026.

After preparing the historical data, 6,522 games were available for model development.

- Training games: 5,217
- Testing games: 1,305

The dataset was split chronologically so older games were used for training and newer games were used for testing.

## Features

The baseline uses team and match-level information:

- Overall win percentage
- Recent five-game form
- Average points scored
- Average points allowed
- Home/away win percentage

All features for a game are calculated using games that occurred before the game being predicted.

## Prediction Output

The model predicts one of two outcomes:

- Home team wins
- Away team wins

The model also provides a probability for each outcome.

## Baseline Evaluation

- Test games: 1,305
- Correct predictions: 798
- Incorrect predictions: 507
- Accuracy: 61.15%

## Limitations

This is an initial baseline model and currently uses only basic team-level historical statistics.

The model does not currently account for:

- Player injuries
- Starting quarterbacks
- Roster changes
- Weather
- Advanced team statistics
- Betting market odds

The purpose of this model is to establish a simple match-prediction baseline that can be evaluated and improved during later sprints.