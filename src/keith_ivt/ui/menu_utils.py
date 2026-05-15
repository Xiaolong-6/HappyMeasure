from __future__ import annotations


def make_touch_menu(root, font_family: str = "Verdana", font_size: int = 10):
    """Create a larger Tk context menu suitable for mouse and touch use."""
    import tkinter as tk
    menu = tk.Menu(root, tearoff=False)
    try:
        menu.configure(
            font=(font_family, max(int(font_size) + 4, 14)),
            borderwidth=2,
            activeborderwidth=0,
            relief="solid",
        )
    except Exception:
        pass
    return menu


def popup_menu(menu, x: int, y: int) -> None:
    try:
        menu.tk_popup(int(x), int(y))
    finally:
        try:
            menu.grab_release()
        except Exception:
            pass
