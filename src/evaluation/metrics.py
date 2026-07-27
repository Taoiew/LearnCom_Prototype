"""Evaluation metrics helpers."""


def accuracy_score(predictions: list[bool], labels: list[bool]) -> float:
    """Compute simple accuracy for boolean predictions."""

    if not predictions or not labels:
        return 0.0
    if len(predictions) != len(labels):
        raise ValueError("Predictions and labels must have the same length")
    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    return correct / len(labels)
