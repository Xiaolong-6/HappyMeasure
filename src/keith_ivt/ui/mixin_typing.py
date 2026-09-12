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

        # Cooperative-mixin hooks used through ``super()`` cannot be satisfied
        # by ``__getattr__`` alone.  Declare their signatures only for static
        # checking; the real methods are supplied by sibling mixins in the app
        # MRO and these declarations do not exist at runtime.
        def start_sweep(self) -> None: ...

        def _current_range_status_fragment(self) -> str: ...

        def _refresh_front_panel_range_widgets(self) -> None: ...

        def _on_mode_changed(self, *_args: Any) -> None: ...
