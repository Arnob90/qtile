from collections import deque
from collections.abc import Callable


class ObservableDeque[T]:
    def __init__(self) -> None:
        self.internal_queue: deque[T] = deque()
        self.push_event: Callable | None = None
        self.pop_event: Callable | None = None

    def push_right(self, item: T):
        self.internal_queue.append(item)
        if self.push_event:
            self.push_event()

    def pop_left(self) -> T:
        to_ret = self.internal_queue.popleft()
        if self.pop_event:
            self.pop_event()
        return to_ret

    def __len__(self) -> int:
        return len(self.internal_queue)
