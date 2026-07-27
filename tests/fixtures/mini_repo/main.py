"""Entry point — ties the ``mini_repo`` fixture's call chain together.

Call chain: ``main.run`` -> ``service.list_widgets`` -> ``repository.get_widget``
-> ``Widget.get_display_name``. Four files, three cross-module call edges, for
pyan3/libcst to resolve during the integration test's indexing pass.
"""

from service import list_widgets


def run() -> list[str]:
    """Build a small batch of widgets and return their display labels."""
    specs = [("Bolt", 0.5), ("Nut", 0.25), ("Washer", 0.1)]
    return list_widgets(specs)


if __name__ == "__main__":
    for label in run():
        print(label)
