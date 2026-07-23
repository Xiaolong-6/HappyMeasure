"""Static typing boundary shared by the composable Tk UI mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


class UiMixinTyping:
    """Tell type checkers that sibling mixins provide application attributes.

    The class is intentionally empty at runtime, so it does not alter attribute
    lookup or hide genuine runtime errors in the composed application.
    """

    if TYPE_CHECKING:

        def __getattr__(self, name: str) -> Any: ...
