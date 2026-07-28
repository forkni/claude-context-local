"""Service layer — orchestrates repository calls for a batch of widget specs."""

from repository import get_widget


def list_widgets(specs: list[tuple[str, float]]) -> list[str]:
    """Return display labels for each ``(name, price)`` spec.

    Calls ``repository.get_widget`` (cross-module function call) and is
    itself called from ``main.run``.
    """
    labels = []
    for name, price in specs:
        _widget, label = get_widget(name, price)
        labels.append(label)
    return labels
