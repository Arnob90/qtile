try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")
    # Continue if ffi not built, so that docs can be built without wayland deps.
    # Provide a stub for FFI to keep going
    from libqtile.backend.wayland.ffi_stub import ffi, lib
import time
import typing
import weakref
from dataclasses import dataclass
from typing import Protocol

from libqtile.core.manager import Qtile

if typing.TYPE_CHECKING:
    # No idea why it's in window.py but it must be important in the future lol
    from libqtile.backend.wayland.core import Core
    from libqtile.backend.wayland.window import Base


class SupportsLerp[T](Protocol):
    def __add__(self, other: T, /) -> T: ...
    def __sub__(self, other: T, /) -> T: ...
    def __mul__(self, scalar: float, /) -> T: ...


def lerp[T: SupportsLerp](a: T, b: T, t: float) -> T:
    return a + (b - a) * t


def clamp(n: float, minn: float, maxn: float) -> float:
    return max(min(maxn, n), minn)


# Using lerp for POC. Will use expo after a bit of experimentation
def ease_out_expo_impl(t: float) -> float:
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    return 1.0 - (2.0 ** (-10.0 * t))


def ease_out_expo[T: SupportsLerp](start: T, end: T, t: float) -> T:
    eased_t = ease_out_expo_impl(t)
    return lerp(start, end, eased_t)


@dataclass
class OtherInfo:
    width: int
    height: int
    borders: typing.Any
    border_count: int
    above: int


@dataclass
class Vector:
    x: float
    y: float

    def __add__(self, other: "Vector") -> "Vector":
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector") -> "Vector":
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scale: float) -> "Vector":
        return Vector(self.x * scale, self.y * scale)


class AnimationManager:
    # Maps window id to a bool that indicates if an animation should be running, set it to false to stop an animation
    # If an animation stops, the corrosponding window id should not exist
    def __init__(self) -> None:
        self._is_first_anim = True

    def animate_first_window(
        self,
        qtile: Qtile,
        win: Base,
        to_pos: Vector,
        to_scale: Vector,
        duration: float,
        info: OtherInfo,
    ):
        ticket = time.time_ns()
        win._anim_ticket = ticket
        win_weak = weakref.ref(win)
        start_time = time.time()
        velocity = 1.0 / duration
        initial_scale = to_scale * 0

        def tick():
            win_ref = win_weak()
            if win_ref is None or win_ref.group is None or win_ref._anim_ticket != ticket:
                return
            elapsed_time = time.time() - start_time
            progress = velocity * elapsed_time
            if progress >= 1:
                win_ref._ptr.place(
                    win_ref._ptr,
                    int(to_pos.x),
                    int(to_pos.y),
                    info.width,
                    info.height,
                    info.borders,
                    info.border_count,
                    int(info.above),
                )
                win_ref.opacity = 1.0
                return
            opacity = ease_out_expo(0.3, 1, progress)
            current_scale = ease_out_expo(initial_scale, to_scale, progress)
            win_ref._ptr.place(
                win_ref._ptr,
                int(to_pos.x),
                int(to_pos.y),
                int(current_scale.x),
                int(current_scale.y),
                info.borders,
                info.border_count,
                int(info.above),
            )
            win_ref.opacity = opacity
            qtile.call_later(0.016, tick)

        tick()

    def animate_to_position(
        self, qtile: Qtile, win: Base, to: Vector, duration: float, info: OtherInfo
    ):
        if win.group is None:
            return
        if len(win.group.windows) == 1 and self._is_first_anim:
            self.animate_first_window(
                qtile, win, to, Vector(info.width, info.height), duration, info
            )
            self._is_first_anim = False
            return
        ticket = time.time_ns()
        win._anim_ticket = ticket
        # MAKE A WEAK POINTER SO WINDOW DOESN'T STAY ALIVE MORE THAN IT NEEDS TO
        win_weak = weakref.ref(win)
        start_time = time.time()
        velocity = 1.0 / duration
        start_vec = Vector(win.x, win.y)
        target_vec = Vector(to.x, to.y)

        def tick():
            win_ref = win_weak()
            elapsed_time = time.time() - start_time
            progress = velocity * elapsed_time
            if win_ref is None or win_ref.group is None or win_ref._anim_ticket != ticket:
                return
            if progress >= 1:
                win_ref._ptr.place(
                    win_ref._ptr,
                    int(to.x),
                    int(to.y),
                    info.width,
                    info.height,
                    info.borders,
                    info.border_count,
                    int(info.above),
                )
            current_vec = ease_out_expo(start_vec, target_vec, progress)
            win_ref._ptr.place(
                win_ref._ptr,
                int(current_vec.x),
                int(current_vec.y),
                info.width,
                info.height,
                info.borders,
                info.border_count,
                int(info.above),
            )
            qtile.call_later(0.016, tick)

        tick()
