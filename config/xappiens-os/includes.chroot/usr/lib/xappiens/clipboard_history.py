"""Session-only clipboard storage. No clipboard contents are written to disk."""

from dataclasses import dataclass
import hashlib


MAX_ITEM_BYTES = 8 * 1024 * 1024
MAX_HISTORY_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 200


@dataclass(frozen=True)
class Entry:
    mime: str
    data: bytes
    digest: bytes

    @property
    def is_image(self):
        return self.mime.startswith("image/")

    @property
    def text(self):
        return self.data.decode("utf-8", errors="replace")


class History:
    def __init__(self, max_items=MAX_ITEMS, max_bytes=MAX_HISTORY_BYTES):
        self.entries = []
        self.max_items = max_items
        self.max_bytes = max_bytes
        self.total_bytes = 0

    def add(self, mime, data):
        if not data or len(data) > min(MAX_ITEM_BYTES, self.max_bytes):
            return False
        if mime.startswith("text/") and not data.strip():
            return False
        digest = hashlib.sha256(mime.encode() + b"\0" + data).digest()
        self.remove(digest)
        self.entries.insert(0, Entry(mime, data, digest))
        self.total_bytes += len(data)
        while len(self.entries) > self.max_items or self.total_bytes > self.max_bytes:
            self.total_bytes -= len(self.entries.pop().data)
        return True

    def remove(self, digest):
        for i, entry in enumerate(self.entries):
            if entry.digest == digest:
                self.total_bytes -= len(self.entries.pop(i).data)
                return True
        return False

    def clear(self):
        self.entries.clear()
        self.total_bytes = 0
