"""Windows desktop runner for the graduate zombie pet.

The Codex custom-pet package controls artwork only.  This companion runner adds
direct manipulation: directional hopping while dragged and a four-way thought
menu that sends the pet to a screen edge and back.
"""

from __future__ import annotations

import argparse
import ctypes
import math
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageTk


CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_WIDTH = 1536
ATLAS_HEIGHT = 2288
TRANSPARENT_KEY = "#ff00ff"


@dataclass(frozen=True)
class Animation:
    row: int
    frame_count: int
    durations_ms: tuple[int, ...]


ANIMATIONS = {
    "idle": Animation(0, 6, (280, 110, 110, 140, 140, 320)),
    "hop-right": Animation(1, 8, (130, 130, 130, 130, 150, 130, 150, 220)),
    "hop-left": Animation(2, 8, (130, 130, 130, 130, 150, 130, 150, 220)),
    "hop-up": Animation(4, 5, (170, 170, 190, 170, 260)),
    "hop-down": Animation(4, 5, (170, 170, 190, 170, 260)),
    "thinking": Animation(8, 6, (150, 150, 150, 150, 150, 280)),
}

INTERACTIVE_FRAME_DIRS = {
    "hop-up": "up",
    "hop-down": "down",
}


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class SpriteAtlas:
    def __init__(self, path: Path, scale: float) -> None:
        self.path = path
        self.scale = scale
        self.image = Image.open(path).convert("RGBA")
        if self.image.size != (ATLAS_WIDTH, ATLAS_HEIGHT):
            raise ValueError(
                f"Expected a v2 1536x2288 spritesheet, got {self.image.size[0]}x{self.image.size[1]}"
            )
        self.width = round(CELL_WIDTH * scale)
        self.height = round(CELL_HEIGHT * scale)
        self.interactive_frames_dir = path.with_name("interactive_frames")
        self._frames: dict[str, list[ImageTk.PhotoImage]] = {}

    def source_frame(self, name: str, animation: Animation, column: int) -> Image.Image:
        external_dir = INTERACTIVE_FRAME_DIRS.get(name)
        if external_dir is not None:
            external_path = self.interactive_frames_dir / external_dir / f"{column:02d}.png"
            if external_path.is_file():
                return Image.open(external_path).convert("RGBA")
        left = column * CELL_WIDTH
        top = animation.row * CELL_HEIGHT
        return self.image.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT))

    def load_tk_frames(self) -> None:
        for name, animation in ANIMATIONS.items():
            frames: list[ImageTk.PhotoImage] = []
            for column in range(animation.frame_count):
                cell = self.source_frame(name, animation, column)
                if self.scale != 1.0:
                    cell = cell.resize((self.width, self.height), Image.Resampling.LANCZOS)
                frames.append(ImageTk.PhotoImage(cell))
            self._frames[name] = frames

    def frame(self, state: str, index: int) -> ImageTk.PhotoImage:
        frames = self._frames[state]
        return frames[index % len(frames)]

    def self_test(self) -> list[str]:
        problems: list[str] = []
        for name, animation in ANIMATIONS.items():
            for column in range(animation.frame_count):
                if name in INTERACTIVE_FRAME_DIRS:
                    external_path = (
                        self.interactive_frames_dir
                        / INTERACTIVE_FRAME_DIRS[name]
                        / f"{column:02d}.png"
                    )
                    if not external_path.is_file():
                        problems.append(f"missing directional frame: {external_path}")
                        continue
                alpha = self.source_frame(name, animation, column).getchannel("A")
                if alpha.getbbox() is None:
                    problems.append(f"{name} frame {column} is empty")
        return problems


class ThoughtPalette:
    DIRECTIONS = (("left", "←"), ("up", "↑"), ("down", "↓"), ("right", "→"))

    def __init__(
        self,
        parent: tk.Tk,
        pet_rect: tuple[int, int, int, int],
        work_area: tuple[int, int, int, int],
        choose: Callable[[str], None],
    ) -> None:
        self.choose = choose
        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=TRANSPARENT_KEY)
        try:
            self.window.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        width, height = 252, 104
        pet_x, pet_y, pet_w, _ = pet_rect
        left, top, right, bottom = work_area
        x = max(left, min(right - width, pet_x + pet_w // 2 - width // 2))
        y = pet_y - height - 8
        if y < top:
            y = min(bottom - height, pet_y + 26)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        canvas = tk.Canvas(
            self.window,
            width=width,
            height=height,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
        )
        canvas.pack()
        canvas.create_oval(10, 14, 242, 100, fill="#fffdf7", outline="#5e6b86", width=2)
        canvas.create_oval(28, 3, 112, 59, fill="#fffdf7", outline="#5e6b86", width=2)
        canvas.create_oval(83, 0, 174, 61, fill="#fffdf7", outline="#5e6b86", width=2)
        canvas.create_oval(146, 5, 225, 60, fill="#fffdf7", outline="#5e6b86", width=2)
        canvas.create_text(126, 23, text="往哪儿蹦？", fill="#26334d", font=("Microsoft YaHei UI", 11, "bold"))

        for index, (direction, arrow) in enumerate(self.DIRECTIONS):
            cx = 42 + index * 56
            tag = f"choice-{direction}"
            canvas.create_oval(
                cx - 20,
                48,
                cx + 20,
                88,
                fill="#dff3ff",
                outline="#4d7ca8",
                width=2,
                tags=(tag,),
            )
            canvas.create_text(
                cx,
                68,
                text=arrow,
                fill="#173f67",
                font=("Segoe UI Symbol", 19, "bold"),
                tags=(tag,),
            )
            canvas.tag_bind(tag, "<Enter>", lambda event, t=tag: self._hover(canvas, t, True))
            canvas.tag_bind(tag, "<Leave>", lambda event, t=tag: self._hover(canvas, t, False))
            canvas.tag_bind(tag, "<Button-1>", lambda event, d=direction: self.choose(d))

    @staticmethod
    def _hover(canvas: tk.Canvas, tag: str, active: bool) -> None:
        items = canvas.find_withtag(tag)
        if items:
            canvas.itemconfigure(items[0], fill="#9edcff" if active else "#dff3ff")

    def close(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()


class DesktopPet:
    def __init__(self, root: tk.Tk, atlas: SpriteAtlas) -> None:
        self.root = root
        self.atlas = atlas
        self.width = atlas.width
        self.height = atlas.height
        self.state = "idle"
        self.frame_index = 0
        self.frame_job: str | None = None
        self.trip_job: str | None = None
        self.palette: ThoughtPalette | None = None
        self.dragging = False
        self.traveling = False
        self.press_root = (0, 0)
        self.last_drag_root = (0, 0)
        self.window_at_press = (0, 0)
        self.press_time = 0.0

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=TRANSPARENT_KEY)
        try:
            root.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            root,
            width=self.width,
            height=self.height,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack()
        self.sprite = self.canvas.create_image(0, 0, anchor="nw")

        work = self.work_area()
        start_x = work[2] - self.width - 48
        start_y = work[3] - self.height - 36
        root.geometry(f"{self.width}x{self.height}+{start_x}+{start_y}")
        self.home = (start_x, start_y)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        root.bind("<Escape>", self.on_escape)

        self.context_menu = tk.Menu(root, tearoff=False)
        self.context_menu.add_command(label="选择蹦跳方向", command=self.show_thoughts)
        self.context_menu.add_command(label="回到初始位置", command=self.return_home)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="退出互动桌宠", command=self.close)

        self.set_state("idle")

    def work_area(self) -> tuple[int, int, int, int]:
        if sys.platform == "win32":
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                            ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

            try:
                user32 = ctypes.windll.user32
                monitor = user32.MonitorFromWindow(self.root.winfo_id(), 2)
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    rect = info.rcWork
                    return rect.left, rect.top, rect.right, rect.bottom
            except Exception:
                pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def position(self) -> tuple[int, int]:
        self.root.update_idletasks()
        return self.root.winfo_x(), self.root.winfo_y()

    def set_state(self, state: str, reset: bool = True) -> None:
        if state not in ANIMATIONS:
            raise KeyError(state)
        if state != self.state or reset:
            self.state = state
            self.frame_index = 0
        self.render_frame()
        if self.frame_job is not None:
            self.root.after_cancel(self.frame_job)
        self.schedule_next_frame()

    def render_frame(self) -> None:
        image = self.atlas.frame(self.state, self.frame_index)
        self.canvas.itemconfigure(self.sprite, image=image)
        self.canvas.image = image

    def schedule_next_frame(self) -> None:
        animation = ANIMATIONS[self.state]
        delay = animation.durations_ms[self.frame_index % animation.frame_count]
        self.frame_job = self.root.after(delay, self.advance_frame)

    def advance_frame(self) -> None:
        animation = ANIMATIONS[self.state]
        self.frame_index = (self.frame_index + 1) % animation.frame_count
        self.render_frame()
        self.schedule_next_frame()

    def on_press(self, event: tk.Event) -> None:
        if self.traveling:
            return
        self.hide_thoughts()
        self.press_root = (event.x_root, event.y_root)
        self.last_drag_root = self.press_root
        self.window_at_press = self.position()
        self.press_time = time.monotonic()
        self.dragging = False

    def on_drag(self, event: tk.Event) -> None:
        if self.traveling:
            return
        dx = event.x_root - self.press_root[0]
        dy = event.y_root - self.press_root[1]
        step_dx = event.x_root - self.last_drag_root[0]
        step_dy = event.y_root - self.last_drag_root[1]
        self.last_drag_root = (event.x_root, event.y_root)
        if abs(dx) + abs(dy) > 5:
            self.dragging = True

        x = self.window_at_press[0] + dx
        y = self.window_at_press[1] + dy
        left, top, right, bottom = self.work_area()
        x = max(left, min(right - self.width, x))
        y = max(top, min(bottom - self.height, y))
        self.root.geometry(f"+{x}+{y}")

        if abs(step_dx) >= abs(step_dy):
            wanted = "hop-right" if step_dx >= 0 else "hop-left"
        else:
            wanted = "hop-down" if step_dy >= 0 else "hop-up"
        if wanted != self.state:
            self.set_state(wanted)

    def on_release(self, _event: tk.Event) -> None:
        if self.traveling:
            return
        elapsed = time.monotonic() - self.press_time
        was_click = not self.dragging and elapsed < 0.55
        self.set_state("idle")
        if was_click:
            self.show_thoughts()

    def show_thoughts(self) -> None:
        if self.traveling:
            return
        self.hide_thoughts()
        x, y = self.position()
        self.set_state("thinking")
        self.palette = ThoughtPalette(
            self.root,
            (x, y, self.width, self.height),
            self.work_area(),
            self.choose_direction,
        )

    def hide_thoughts(self) -> None:
        if self.palette is not None:
            self.palette.close()
            self.palette = None

    def choose_direction(self, direction: str) -> None:
        self.hide_thoughts()
        self.start_trip(direction)

    @staticmethod
    def ease(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def start_trip(self, direction: str) -> None:
        if self.traveling:
            return
        start_x, start_y = self.position()
        left, top, right, bottom = self.work_area()
        targets = {
            "left": (left, start_y),
            "right": (right - self.width, start_y),
            "up": (start_x, top),
            "down": (start_x, bottom - self.height),
        }
        target_x, target_y = targets[direction]
        target_x = max(left, min(right - self.width, target_x))
        target_y = max(top, min(bottom - self.height, target_y))
        distance = math.hypot(target_x - start_x, target_y - start_y)
        if distance < 2:
            self.set_state("idle")
            return

        opposite = {"left": "right", "right": "left", "up": "down", "down": "up"}

        def waypoints(
            origin: tuple[int, int], destination: tuple[int, int]
        ) -> list[tuple[int, int]]:
            span = math.hypot(destination[0] - origin[0], destination[1] - origin[1])
            count = max(1, math.ceil(span / 130.0))
            return [
                (
                    round(origin[0] + (destination[0] - origin[0]) * index / count),
                    round(origin[1] + (destination[1] - origin[1]) * index / count),
                )
                for index in range(count + 1)
            ]

        outward = waypoints((start_x, start_y), (target_x, target_y))
        homeward = waypoints((target_x, target_y), (start_x, start_y))
        segments: list[tuple[str, tuple[int, int], tuple[int, int]]] = []
        segments.extend((direction, outward[i], outward[i + 1]) for i in range(len(outward) - 1))
        turn_index = len(segments)
        return_direction = opposite[direction]
        segments.extend(
            (return_direction, homeward[i], homeward[i + 1])
            for i in range(len(homeward) - 1)
        )

        self.traveling = True
        self.set_state(f"hop-{direction}")

        def run_segment(index: int) -> None:
            if index >= len(segments):
                self.root.geometry(f"+{start_x}+{start_y}")
                self.traveling = False
                self.trip_job = None
                self.set_state("idle")
                return

            segment_direction, origin, destination = segments[index]
            wanted_state = f"hop-{segment_direction}"
            if wanted_state != self.state:
                self.set_state(wanted_state)

            started = time.perf_counter()
            hop_duration = 0.92

            def animate_hop() -> None:
                elapsed = time.perf_counter() - started
                progress = min(1.0, elapsed / hop_duration)
                moved = self.ease(progress)
                x = origin[0] + (destination[0] - origin[0]) * moved
                y = origin[1] + (destination[1] - origin[1]) * moved

                arc = math.sin(progress * math.pi)
                if segment_direction in ("left", "right"):
                    y -= arc * min(30.0, 20.0 + self.atlas.scale * 8.0)
                else:
                    x += arc * (7.0 if segment_direction == "up" else -7.0)

                x = max(left, min(right - self.width, round(x)))
                y = max(top, min(bottom - self.height, round(y)))
                self.root.geometry(f"+{x}+{y}")

                if progress < 1.0:
                    self.trip_job = self.root.after(16, animate_hop)
                    return

                self.root.geometry(f"+{destination[0]}+{destination[1]}")
                next_delay = 420 if index + 1 == turn_index else 170
                self.trip_job = self.root.after(next_delay, lambda: run_segment(index + 1))

            animate_hop()

        run_segment(0)

    def return_home(self) -> None:
        if self.traveling:
            return
        self.hide_thoughts()
        self.root.geometry(f"+{self.home[0]}+{self.home[1]}")
        self.set_state("idle")

    def show_context_menu(self, event: tk.Event) -> None:
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def on_escape(self, _event: tk.Event) -> None:
        if self.palette is not None:
            self.hide_thoughts()
            self.set_state("idle")
        elif not self.traveling:
            self.return_home()

    def close(self) -> None:
        self.hide_thoughts()
        if self.trip_job is not None:
            self.root.after_cancel(self.trip_job)
        if self.frame_job is not None:
            self.root.after_cancel(self.frame_job)
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive graduate zombie desktop pet")
    parser.add_argument(
        "--sprite",
        type=Path,
        default=Path(__file__).with_name("spritesheet.webp"),
        help="Path to the v2 spritesheet",
    )
    parser.add_argument("--scale", type=float, default=1.0, help="Display scale from 0.6 to 1.8")
    parser.add_argument("--self-test", action="store_true", help="Validate assets without opening a window")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scale = max(0.6, min(1.8, args.scale))
    atlas = SpriteAtlas(args.sprite.resolve(), scale)
    problems = atlas.self_test()
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    if args.self_test:
        print("interactive_pet self-test: ok")
        return 0

    enable_windows_dpi_awareness()
    root = tk.Tk()
    atlas.load_tk_frames()
    DesktopPet(root, atlas)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
