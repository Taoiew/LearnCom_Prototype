"""Evaluation entry points for model outputs."""

from .metrics import accuracy_score


class Evaluator:
    """Simple wrapper around evaluation metrics."""

    def evaluate(self, predictions: list[bool], labels: list[bool]) -> float:
        return accuracy_score(predictions, labels)
