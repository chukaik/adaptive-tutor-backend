"""
In-memory stand-ins for Firestore and the OpenAI client.

FakeFirestore implements only the parts of the google-cloud-firestore API
this app uses: collections and sub-collections, document get/set/update/
delete, add, where("==") / order_by / limit / stream, and the
SERVER_TIMESTAMP and Increment sentinels.
"""
import copy
import itertools
from datetime import datetime, timezone
from unittest.mock import MagicMock

from google.cloud.exceptions import NotFound
from google.cloud.firestore_v1.transforms import Increment, Sentinel


def _resolve(value, current=None):
    if isinstance(value, Sentinel):          # SERVER_TIMESTAMP
        return datetime.now(timezone.utc)
    if isinstance(value, Increment):
        return (current or 0) + value.value
    return copy.deepcopy(value)


class FakeSnapshot:
    def __init__(self, ref, data):
        self.reference = ref
        self.id = ref.id
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data is not None else None


class FakeDocumentRef:
    def __init__(self, db, path):
        self._db = db
        self.path = path
        self.id = path[-1]

    def get(self):
        return FakeSnapshot(self, self._db.docs.get(self.path))

    def set(self, data):
        self._db.docs[self.path] = {k: _resolve(v) for k, v in data.items()}

    def update(self, data):
        if self.path not in self._db.docs:
            raise NotFound(f"No document to update: {'/'.join(self.path)}")
        doc = self._db.docs[self.path]
        for key, value in data.items():
            doc[key] = _resolve(value, doc.get(key))

    def delete(self):
        self._db.docs.pop(self.path, None)

    def collection(self, name):
        return FakeQuery(self._db, self.path + (name,))


class FakeQuery:
    """A collection reference, or a query built from one."""

    def __init__(self, db, path, filters=(), order=None, limit=None):
        self._db = db
        self.path = path
        self._filters = filters
        self._order = order
        self._limit = limit

    def document(self, doc_id=None):
        return FakeDocumentRef(self._db, self.path + (doc_id or self._db.new_id(),))

    def add(self, data):
        ref = self.document()
        ref.set(data)
        return (datetime.now(timezone.utc), ref)

    def where(self, field, op, value):
        if op != "==":
            raise NotImplementedError(f"FakeFirestore supports only '==', got {op!r}")
        return FakeQuery(self._db, self.path, self._filters + ((field, value),),
                         self._order, self._limit)

    def order_by(self, field, direction="ASCENDING"):
        return FakeQuery(self._db, self.path, self._filters, (field, direction), self._limit)

    def limit(self, n):
        return FakeQuery(self._db, self.path, self._filters, self._order, n)

    def stream(self):
        depth = len(self.path) + 1
        refs = [
            FakeDocumentRef(self._db, path)
            for path in list(self._db.docs)
            if len(path) == depth and path[:-1] == self.path
        ]
        snaps = [ref.get() for ref in refs]
        snaps = [s for s in snaps
                 if all(s._data.get(f) == v for f, v in self._filters)]
        if self._order:
            field, direction = self._order
            # Firestore leaves out documents that lack the order_by field
            snaps = [s for s in snaps if field in s._data]
            snaps.sort(key=lambda s: s._data[field],
                       reverse=(direction == "DESCENDING"))
        if self._limit is not None:
            snaps = snaps[: self._limit]
        return iter(snaps)


class FakeFirestore:
    def __init__(self):
        self.docs = {}                      # path tuple -> dict
        self._ids = itertools.count(1)

    def new_id(self):
        return f"auto{next(self._ids):04d}"

    def collection(self, name):
        return FakeQuery(self, (name,))

    # Helpers for tests
    def put(self, collection, doc_id, data):
        self.docs[(collection, doc_id)] = copy.deepcopy(data)

    def doc(self, *path):
        return self.docs.get(tuple(path))

    def all(self, collection):
        return {p[1]: d for p, d in self.docs.items() if len(p) == 2 and p[0] == collection}


class FakeOpenAI:
    """
    Stand-in for openai.OpenAI. Queue reply texts in .replies; every request
    is recorded in .requests. A call with no queued reply fails the test.
    """

    def __init__(self):
        self.replies = []
        self.requests = []
        self.chat = MagicMock()
        self.chat.completions.create = self._create

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.replies:
            raise AssertionError("Unexpected OpenAI call: no reply queued in the test")
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = self.replies.pop(0)
        return response
