import pandas as pd

from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


DATA_PATH = Path("data/processed/nfl_model_data.csv")


FEATURES = [
    "home_win_pct",
    "away_win_pct",
    "home_recent_form",
    "away_recent_form",
    "home_avg_scored",
    "away_avg_scored",
    "home_avg_allowed",
    "away_avg_allowed",
    "home_home_win_pct",
    "away_away_win_pct",
]


def load_model_data():
    """Load the processed NFL model dataset."""

    return pd.read_csv(DATA_PATH)


def split_data(data):
    """Use older games for training and newer games for testing."""

    data = data.sort_values("gameday").reset_index(drop=True)

    split_index = int(len(data) * 0.80)

    train_data = data.iloc[:split_index]
    test_data = data.iloc[split_index:]

    return train_data, test_data


def train_model(train_data):
    """Train the Logistic Regression baseline."""

    X_train = train_data[FEATURES]
    y_train = train_data["outcome"]

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(max_iter=1000),
            ),
        ]
    )

    model.fit(X_train, y_train)

    return model


def evaluate_model(model, test_data):
    """Evaluate the model on held-out historical games."""

    X_test = test_data[FEATURES]
    y_test = test_data["outcome"]

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)

    accuracy = accuracy_score(y_test, predictions)

    correct = int((predictions == y_test).sum())
    incorrect = len(y_test) - correct

    return accuracy, correct, incorrect, predictions, probabilities


def main():

    data = load_model_data()

    train_data, test_data = split_data(data)

    print(f"Total games: {len(data)}")
    print(f"Training games: {len(train_data)}")
    print(f"Testing games: {len(test_data)}")

    print("\nTraining Logistic Regression baseline...")

    model = train_model(train_data)

    (
        accuracy,
        correct,
        incorrect,
        predictions,
        probabilities,
    ) = evaluate_model(model, test_data)

    print("\nBaseline evaluation")
    print(f"Test games: {len(test_data)}")
    print(f"Correct predictions: {correct}")
    print(f"Incorrect predictions: {incorrect}")
    print(f"Accuracy: {accuracy:.2%}")

    sample = test_data[
        [
            "gameday",
            "home_team",
            "away_team",
            "outcome",
        ]
    ].copy()

    sample["prediction"] = predictions
    sample["away_win_probability"] = probabilities[:, 0]
    sample["home_win_probability"] = probabilities[:, 1]

    print("\nSample predictions:")

    for _, game in sample.head(10).iterrows():

        predicted_team = (
            game["home_team"]
            if game["prediction"] == 1
            else game["away_team"]
        )

        actual_team = (
            game["home_team"]
            if game["outcome"] == 1
            else game["away_team"]
        )

        print(f"\n{game['away_team']} @ {game['home_team']}")

        print(
            f"Away win probability: "
            f"{game['away_win_probability']:.1%}"
        )

        print(
            f"Home win probability: "
            f"{game['home_win_probability']:.1%}"
        )

        print(f"Predicted winner: {predicted_team}")
        print(f"Actual winner: {actual_team}")


if __name__ == "__main__":
    main()