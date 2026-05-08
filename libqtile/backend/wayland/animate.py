try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import lib
except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")
    # Continue if ffi not built, so that docs can be built without wayland deps.
    # Provide a stub for FFI to keep going
    from libqtile.backend.wayland.ffi_stub import lib
import time
import typing
import weakref
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from libqtile.backend.wayland.observable_deque import ObservableDeque

if typing.TYPE_CHECKING:
    # No idea why it's in window.py but it must be important in the future lol
    from libqtile.backend.wayland.window import Base
    from libqtile.core.manager import Qtile


class SupportsLerp[T](Protocol):
    def __add__(self, other: T, /) -> T: ...
    def __sub__(self, other: T, /) -> T: ...
    def __mul__(self, scalar: float, /) -> T: ...


def lerp[T: SupportsLerp](a: T, b: T, t: float) -> T:
    return a + (b - a) * t


def clamp(n: float, minn: float, maxn: float) -> float:
    return max(min(maxn, n), minn)


def ease_out_expo(t: float) -> float:
    if t == 0.0:
        return 0.0
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


class IAnimationManager(ABC):
    @abstractmethod
    def animate_to_position(
        self,
        win: Base,
        from_pos: Vector,
        to_pos: Vector,
        to_scale: Vector,
        info: OtherInfo,
    ):
        pass

    @abstractmethod
    def animate_fly_away(self, win: Base, direction: Vector, callback: Callable):
        pass

    @abstractmethod
    def finalize_init(self, qtile: Qtile):
        """Qtile object is supposed to be passed in here"""


class NoOpAnimationManager(IAnimationManager):
    def animate_fly_away(self, win: Base, direction: Vector, callback: Callable):
        callback()

    def animate_to_position(
        self, win: Base, from_pos: Vector, to_pos: Vector, to_scale: Vector, info: OtherInfo
    ):
        win._ptr.place(
            win._ptr,
            int(to_pos.x),
            int(to_pos.y),
            int(to_scale.x),
            int(to_scale.y),
            info.borders,
            info.border_count,
            int(info.above),
        )

    def finalize_init(self, qtile: Qtile):
        pass


class QtilelessException(Exception):
    pass


class AnimationManager(IAnimationManager):
    def __init__(self) -> None:
        self._is_first_anim = True
        self._scheduled_callbacks_queue: ObservableDeque[Callable[[float], bool]] = (
            ObservableDeque()
        )
        self._qtile: Qtile | None = None
        # Get time in ms
        self._current_time_ms = int(time.time() * 1000)
        self._is_running = False
        self._scheduled_callbacks_queue.push_event = self._wake_up
        self.easing_fn: Callable[[float], float] = ease_out_expo
        self.duration = 0.5

    @property
    def qtile(self) -> Qtile:
        # TODO: Add a fallback instead of exception
        if self._qtile is None:
            raise QtilelessException("Qtile was never set. Maybe you forgot to override it?")
        return self._qtile

    def finalize_init(self, qtile: Qtile):
        self._qtile = qtile

    def _wake_up(self):
        """Triggered by push_right. Only starts the loop if it's not already running."""
        if not self._is_running:
            self._is_running = True
            # We use 0.001 (1ms) to ensure ALL windows from a layout change
            # are pushed into the queue before the first tick runs.
            self.qtile.call_later(0.001, self._main_loop)

    def _main_loop(self):
        if not self._scheduled_callbacks_queue.internal_queue:
            self._is_running = False
            return

        # THE SHARED CLOCK: Every window in this frame uses this exact time.
        now = time.time()

        # SNAPSHOT the current queue size.
        # We only process the windows that are in the queue right NOW.
        # This defines one single 'Frame'.
        tasks_this_frame = len(self._scheduled_callbacks_queue)

        for _ in range(tasks_this_frame):
            # pop_left and execute
            callback = self._scheduled_callbacks_queue.pop_left()

            # The callback must take 'now' as an argument and return:
            # True -> I want to run again next frame
            # False -> I am finished or I have been preempted
            if callback(now):
                # Re-queue for the next frame
                # (Note: This won't trigger _wake_up because _is_running is True)
                self._scheduled_callbacks_queue.push_right(callback)

        # If anyone re-queued, schedule the next frame in 16ms
        if self._scheduled_callbacks_queue.internal_queue:
            self.qtile.call_later(0.016, self._main_loop)
        else:
            self._is_running = False

    def animate_first_window(
        self,
        win: Base,
        to_pos: Vector,
        to_scale: Vector,
        info: OtherInfo,
    ):
        if win._anim_ticket or win._do_not_interrupt_anim or win.group is None:
            return
        ticket = time.time_ns()
        win._anim_ticket = ticket
        win_weak = weakref.ref(win)
        start_time = time.time()
        velocity = 1.0 / self.duration
        initial_scale = to_scale * 0.1
        center = to_pos + (to_scale * 0.5)

        def tick(now: float) -> bool:
            win_ref = win_weak()
            if win_ref is None or win_ref.group is None:
                return False
            if win_ref._anim_ticket != ticket:
                win_ref.opacity = 1.0
                return False
            elapsed_time = now - start_time
            progress = velocity * elapsed_time
            if progress >= 1:
                win_ref._ptr.place(
                    win_ref._ptr,
                    int(to_pos.x),
                    int(to_pos.y),
                    int(to_scale.x),
                    int(to_scale.y),
                    info.borders,
                    info.border_count,
                    int(info.above),
                )
                win_ref.opacity = 1.0
                return False
            eased = self.easing_fn(progress)
            opacity = lerp(0.3, 1, eased)
            current_scale = lerp(initial_scale, to_scale, eased)
            current_pos = center - current_scale * 0.5
            win_ref._ptr.place(
                win_ref._ptr,
                int(current_pos.x),
                int(current_pos.y),
                int(current_scale.x),
                int(current_scale.y),
                info.borders,
                info.border_count,
                int(info.above),
            )
            win_ref.opacity = opacity
            return True

        self._scheduled_callbacks_queue.push_right(tick)

    def animate_to_position(
        self,
        win: Base,
        from_pos: Vector,
        to_pos: Vector,
        to_scale: Vector,
        info: OtherInfo,
    ):
        # if the window is dying, DO NOT INTERRUPT
        if win.group is None or getattr(win, "_do_not_interrupt_anim", False):
            return

        if len(win.group.windows) == 1 and self._is_first_anim:
            self.animate_first_window(win, to_pos, Vector(info.width, info.height), info)
            self._is_first_anim = False
            return

        ticket = time.time_ns()
        win._anim_ticket = ticket
        # MAKE A WEAK POINTER SO WINDOW DOESN'T STAY ALIVE MORE THAN IT NEEDS TO
        win_weak = weakref.ref(win)
        start_time = time.time()
        velocity = 1.0 / self.duration

        # 1. SETUP THE STARTING EDGES
        start_scale = Vector(win.width, win.height)
        start_left = float(from_pos.x)
        start_right = float(from_pos.x + start_scale.x)
        start_top = float(from_pos.y)
        start_bottom = float(from_pos.y + start_scale.y)

        # 2. SETUP THE TARGET EDGES
        target_left = float(to_pos.x)
        target_right = float(to_pos.x + to_scale.x)
        target_top = float(to_pos.y)
        target_bottom = float(to_pos.y + to_scale.y)

        def tick(now: float):
            win_ref = win_weak()
            elapsed_time = now - start_time
            progress = clamp(velocity * elapsed_time, 0.0, 1.0)

            if (
                win_ref is None
                or win_ref.group is None
                or getattr(win_ref, "_anim_ticket", None) != ticket
            ):
                # Release ownership just in case
                # Retaking it is the next animation's responsiblity
                return False

            if progress >= 1.0:
                # Final Snap
                win_ref._ptr.place(
                    win_ref._ptr,
                    int(to_pos.x),
                    int(to_pos.y),
                    int(to_scale.x),
                    int(to_scale.y),
                    info.borders,
                    info.border_count,
                    int(info.above),
                )
                return False

            eased = self.easing_fn(progress)  # Assuming this takes a single float now

            # 3. INTERPOLATE THE EDGES DIRECTLY
            cur_left = lerp(start_left, target_left, eased)
            cur_right = lerp(start_right, target_right, eased)
            cur_top = lerp(start_top, target_top, eased)
            cur_bottom = lerp(start_bottom, target_bottom, eased)

            # 4. DERIVE X, Y, WIDTH, HEIGHT FROM EDGES
            # X and Y are always the Left and Top edges
            cur_x = int(cur_left)
            cur_y = int(cur_top)
            # Width and Height are the distances between the edges
            cur_w = int(cur_right - cur_left)
            cur_h = int(cur_bottom - cur_top)

            # 5. CALL C
            win_ref._ptr.place(
                win_ref._ptr,
                cur_x,
                cur_y,
                cur_w,
                cur_h,
                info.borders,
                info.border_count,
                int(info.above),
            )
            return True

        self._scheduled_callbacks_queue.push_right(tick)

    def kill_last_window(
        self,
        win: Base,
        from_scale: Vector,
        info: OtherInfo,
    ):
        ticket = time.time_ns()
        win._anim_ticket = ticket
        win_weak = weakref.ref(win)

        start_time = time.time()
        velocity = 1.0 / self.duration

        start_pos = Vector(float(win.x), float(win.y))
        start_size = from_scale
        center = start_pos + (start_size * 0.5)
        end_size = Vector(0, 0)

        def tick(now: float):
            win_ref = win_weak()
            if win_ref is None or win_ref._anim_ticket != ticket:
                return False

            elapsed = now - start_time
            progress = clamp(elapsed * velocity, 0.0, 1.0)
            eased = self.easing_fn(progress)

            if progress >= 1.0:
                win_ref._ptr.kill(win_ref._ptr)
                return False

            cur_size = lerp(start_size, end_size, eased)
            cur_pos = center - (cur_size * 0.5)

            win_ref._ptr.place(
                win_ref._ptr,
                int(cur_pos.x),
                int(cur_pos.y),
                int(cur_size.x),
                int(cur_size.y),
                info.borders,
                info.border_count,
                int(info.above),
            )
            # Fade out
            win_ref.opacity = lerp(1.0, 0.0, progress)
            return True

        self._scheduled_callbacks_queue.push_right(tick)

    def animate_fly_away(self, win: Base, direction: Vector, callback: Callable):
        ticket = time.time_ns()
        win._anim_ticket = ticket
        win_weak = weakref.ref(win)

        start_pos = Vector(win.x, win.y)
        # Move it 1000 pixels in the chosen direction (e.g., Vector(1920, 0) for right)
        target_pos = start_pos + direction
        start_time = time.time()
        velocity = 1.0 / self.duration

        def tick(now: float) -> bool:
            elasped_time = now - start_time
            w = win_weak()
            if not w or w._anim_ticket != ticket:
                return False

            progress = clamp(velocity * elasped_time, 0, 1)
            eased = self.easing_fn(progress)
            cur_pos = lerp(start_pos, target_pos, eased)
            # Update visuals only
            lib.qw_view_set_position(w._ptr, int(cur_pos.x), int(cur_pos.y))
            w.opacity = lerp(1.0, 0.0, eased)

            if progress < 1.0:
                return True
            else:
                # ANIMATION DONE: Now do the real logic
                callback()
                w.opacity = 1.0
                return False

        self._scheduled_callbacks_queue.push_right(tick)


class AnimationManagerBuilder:
    def __init__(self) -> None:
        self.built_manager = AnimationManager()

    def with_duration(self, duration: float):
        self.built_manager.duration = duration
        return self

    def with_ease_fn(self, easing_fn: Callable[[float], float]):
        self.built_manager.easing_fn = easing_fn
        return self

    def build(self):
        return self.built_manager
