"""Trains the ticket classifier.

Run it from the project root:
    python -m ml.train
"""

import csv
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "tickets.csv"
OUT_PATH = ROOT / "artifacts" / "classifier.joblib"

TARGETS = ("category", "priority")


def load_data(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    texts = []
    labels = {target: [] for target in TARGETS}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"])
            for target in TARGETS:
                labels[target].append(row[target])
    return texts, labels


def build_pipeline() -> Pipeline:
    # words catch the topic, character n-grams help with typos and word forms
    features = FeatureUnion(
        [
            ("words", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ]
    )
    return Pipeline([("features", features), ("clf", LogisticRegression(C=10, max_iter=1000))])


def train(data_path: Path = DATA_PATH, out_path: Path = OUT_PATH) -> dict:
    texts, labels = load_data(data_path)
    models = {}
    metrics = {"samples": len(texts)}

    for target in TARGETS:
        y = labels[target]
        x_train, x_test, y_train, y_test = train_test_split(
            texts, y, test_size=0.2, stratify=y, random_state=42
        )

        # first check how good it is on data it has not seen
        pipe = build_pipeline().fit(x_train, y_train)
        preds = pipe.predict(x_test)
        metrics[target] = {
            "accuracy": round(accuracy_score(y_test, preds), 3),
            "report": classification_report(y_test, preds, output_dict=True, zero_division=0),
        }

        # the model we ship is trained on everything, the dataset is tiny
        models[target] = build_pipeline().fit(texts, y)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(models, out_path)
    (out_path.parent / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    result = train()
    print(f"trained on {result['samples']} tickets")
    for target in TARGETS:
        print(f"{target} accuracy on held out set: {result[target]['accuracy']}")
    print(f"saved model to {OUT_PATH}")
