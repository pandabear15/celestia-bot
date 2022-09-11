import threading
from message_model import MessageModel


class MessageCache:
    _lock: threading.Lock = None
    _max_cache_size: int = None
    _cache: list[MessageModel] = None

    def __init__(self, max_cache_size: int):
        self._lock = threading.Lock()
        self._max_cache_size = max_cache_size
        self._cache = []

    def add_message_model(self, message: MessageModel, append: bool = True):
        self._lock.acquire()
        try:
            if append:
                self._cache.append(message)
            else:
                left: int = 0
                right: int = len(self._cache) - 1
                while left <= right:
                    mid = (left + right) // 2
                    if self._cache[mid] < message:
                        left = mid + 1
                    elif self._cache[mid] > message:
                        right = mid - 1
                    else:
                        left = mid
                        break
                self._cache.insert(left, message)
            if len(self._cache) > self._max_cache_size:
                self._cache = (self._cache.append(message))[-self._max_cache_size:]
        finally:
            self._lock.release()

    def get_message_model(self, message: MessageModel, update: bool = False) -> MessageModel | None:
        self._lock.acquire()
        ret_value = None
        try:
            left: int = 0
            right: int = len(self._cache) - 1
            while left <= right:
                mid = (left + right) // 2
                if self._cache[mid] < message:
                    left = mid + 1
                elif self._cache[mid] > message:
                    right = mid - 1
                else:
                    ret_value = self._cache[mid]
                    if update:
                        self._cache[mid] = message
                    break
        finally:
            self._lock.release()
        return ret_value

    def len(self):
        return len(self._cache)

    def __sizeof__(self) -> int:
        cache_mem_size = 0
        for i in range(self.len()):
            cache_mem_size += self._cache[i].__sizeof__()
        return cache_mem_size + self._cache.__sizeof__()
