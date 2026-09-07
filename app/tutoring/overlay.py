import tkinter as tk


class HighlightOverlay:
    """Displays a non-blocking visual highlight around a screen region."""

    def __init__(self):
        self.root = None
        self.canvas = None

    def show(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        duration: float = 0,
    ) -> None:
        """Show a highlight without blocking the application."""

        self.close()

        self.root = tk.Tk()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes(
            "-transparentcolor",
            "black",
        )

        self.root.geometry(
            f"{width}x{height}+{x}+{y}"
        )

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg="black",
            highlightthickness=0,
        )

        self.canvas.pack()

        self.canvas.create_rectangle(
            2,
            2,
            max(width - 2, 2),
            max(height - 2, 2),
            outline="red",
            width=4,
        )

        self.root.update_idletasks()
        self.root.update()

        if duration > 0:
            self.root.after(
                int(duration * 1000),
                self.close,
            )

    def update(self) -> None:
        """Process pending overlay events."""

        if self.root is None:
            return

        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            self.root = None
            self.canvas = None

    def close(self) -> None:
        """Close the highlight overlay."""

        if self.root is not None:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

        self.root = None
        self.canvas = None