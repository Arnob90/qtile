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
from dataclasses import dataclass
from typing import Protocol

from libqtile.core.manager import Qtile

if typing.TYPE_CHECKING:
    # No idea why it's in window.py but it must be important in the future lol
    from libqtile.backend.wayland.core import Core


class SupportsLerp[T](Protocol):
    def __add__(self, other: T, /) -> T: ...
    def __sub__(self, other: T, /) -> T: ...
    def __mul__(self, scalar: float, /) -> T: ...


def lerp[T: SupportsLerp](a: T, b: T, t: T) -> float:
    return a + (b - a) * t


def clamp(n: float, minn: float, maxn: float) -> float:
    return max(min(maxn, n), minn)


# Using lerp for POC. Will use expo after a bit of experimentation
def ease_out_expo(t: float) -> float:
    if t == 1.0:
        return 1.0
    return 1.0 - (2.0 ** (-10.0 * t))


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
    _win_id_to_active_animation_task_cancel: dict[int, bool] = {}

    def __init__(self, qtile: Qtile, wind_id: int) -> None:
        self.qtile = qtile
        self._wind_id = wind_id

    def animate_to_position(
        self, to: Vector, ptr: ffi.CData, time_to_finish: float, other_info: OtherInfo
    ):
        if self._wind_id in AnimationManager._win_id_to_active_animation_task_cancel:
            AnimationManager._win_id_to_active_animation_task_cancel[self._wind_id] = False
            # Wait 0.07 seconds to be safe
            # We must not start the animation before the previous one is stopped
            # Lest we segfault
            self.qtile.call_later(
                0.017, self.animate_to_position, to, ptr, time_to_finish, other_info
            )
            return
        print("I am animating")
        start_time = time.time()
        velocity = 1.0 / time_to_finish
        start_x = to.x - 500
        print(f"From: {start_x}, to:{to.x}")

        def tick():
            if (
                self._wind_id not in self._win_id_to_active_animation_task_cancel
                or not self._win_id_to_active_animation_task_cancel[self._wind_id]
            ):
                return
            time_elapsed = time.time() - start_time
            progress = clamp(velocity * time_elapsed, 0, 1)
            if progress >= 1:
                self._win_id_to_active_animation_task_cancel.pop(self._wind_id)
                return
            current_x = int(lerp(start_x, to.x, progress))
            ptr.place(
                ptr,
                current_x,
                int(to.y),
                other_info.width,
                other_info.height,
                other_info.borders,
                other_info.border_count,
                int(other_info.above),
            )
            # Let's aim for 60FPS
            self.qtile.call_later(0.016, tick)
            print(f"current_x: {current_x}")
            print(f"progress: {progress}")

        AnimationManager._win_id_to_active_animation_task_cancel.update({self._wind_id: True})
        tick()
