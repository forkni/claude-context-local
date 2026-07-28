"""Repository layer — constructs ``Widget`` instances, calls into ``models.py``."""

from models import Widget


def get_widget(name: str, price: float) -> tuple[Widget, str]:
    """Build a ``Widget`` and return it with its display label.

    Calls ``Widget.get_display_name`` (cross-module method call) and is
    itself called from ``service.list_widgets`` (cross-module function call).
    """
    widget = Widget(name, price)
    label = widget.get_display_name()
    return widget, label
