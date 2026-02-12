from sqlalchemy.types import JSON, TEXT, TypeDecorator
from sqlalchemy.dialects.postgresql import TSVECTOR

try:
    from pgvector.sqlalchemy import Vector as PgVector
except Exception:  # pragma: no cover - optional dependency
    PgVector = None


class VectorType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PgVector is not None:
            return dialect.type_descriptor(PgVector(self.dim))
        return dialect.type_descriptor(JSON)


class SearchVectorType(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR)
        return dialect.type_descriptor(TEXT)
