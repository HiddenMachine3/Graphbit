"""Integration test for suggestions endpoint on Postgres with pgvector."""

import asyncio
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.session import get_db
from app.models import Base, AppUser as AppUserModel, Project as ProjectModel, Node as NodeModel, Material as MaterialModel


class _FakeGeminiResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _fake_gemini_post(url, json=None, timeout=None, verify=None):
    if ":embedContent" in url:
        return _FakeGeminiResponse({"embedding": {"values": [0.1] * 768}})

    if ":generateContent" in url:
        return _FakeGeminiResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"phrases": ["graph", "search"]}'
                                }
                            ]
                        }
                    }
                ]
            }
        )

    raise AssertionError(f"Unexpected Gemini endpoint: {url}")


def test_postgres_suggestions_endpoint(monkeypatch):
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    postgres_url = os.getenv("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set")

    schema_name = f"test_suggest_{uuid.uuid4().hex[:8]}"
    engine = create_async_engine(postgres_url, poolclass=NullPool)
    engine = engine.execution_options(schema_translate_map={None: schema_name})
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db():
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            session.add(
                AppUserModel(
                    id="admin",
                    username="admin",
                    name="admin",
                    password_hash="admin",
                )
            )
            session.add(
                ProjectModel(
                    id="proj-suggest-int",
                    name="Suggest Project",
                    description="Integration test",
                    owner_id="admin",
                    created_by="admin",
                    visibility="private",
                )
            )
            session.add(
                NodeModel(
                    id="node-suggest-1",
                    project_id="proj-suggest-int",
                    created_by="admin",
                    topic_name="Graph Basics",
                    proven_knowledge_rating=0.2,
                    user_estimated_knowledge_rating=0.2,
                    importance=0.6,
                    relevance=0.6,
                    view_frequency=1,
                    source_material_ids=[],
                    embedding=[0.1] * 768,
                )
            )
            session.add(
                MaterialModel(
                    id="mat-suggest-int",
                    project_id="proj-suggest-int",
                    created_by="admin",
                    title="Graph Material",
                    content_text="Graph theory basics",
                )
            )
            await session.commit()
            await session.execute(
                text(
                    "UPDATE nodes SET search_vector = to_tsvector('english', COALESCE(topic_name, '')) "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": "proj-suggest-int"},
            )
            await session.commit()

    async def drop_db():
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await engine.dispose()

    asyncio.run(init_db())

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(
        "app.services.node_suggestions.embedding_service.requests.post",
        _fake_gemini_post,
    )
    monkeypatch.setattr(
        "app.services.node_suggestions.keyword_extraction_service.requests.post",
        _fake_gemini_post,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/materials/mat-suggest-int/suggestions",
                json={
                    "project_id": "proj-suggest-int",
                    "threshold": 0.7,
                    "semantic_weight": 0.6,
                    "keyword_weight": 0.4,
                    "top_k": 20,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert "strong" in payload
            assert "weak" in payload
            suggestions = payload["strong"] + payload["weak"]
            assert len(suggestions) > 0
            assert any(item.get("suggestion_type") in {"EXISTING", "NEW"} for item in suggestions)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(drop_db())


def test_postgres_question_raw_text_suggestions_endpoint(monkeypatch):
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    postgres_url = os.getenv("POSTGRES_TEST_URL")
    if not postgres_url:
        pytest.skip("POSTGRES_TEST_URL not set")

    schema_name = f"test_suggest_q_{uuid.uuid4().hex[:8]}"
    engine = create_async_engine(postgres_url, poolclass=NullPool)
    engine = engine.execution_options(schema_translate_map={None: schema_name})
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db():
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            session.add(
                AppUserModel(
                    id="admin",
                    username="admin",
                    name="admin",
                    password_hash="admin",
                )
            )
            session.add(
                ProjectModel(
                    id="proj-suggest-q-int",
                    name="Suggest Question Project",
                    description="Question integration test",
                    owner_id="admin",
                    created_by="admin",
                    visibility="private",
                )
            )
            session.add(
                NodeModel(
                    id="node-suggest-q-1",
                    project_id="proj-suggest-q-int",
                    created_by="admin",
                    topic_name="Graph Search",
                    proven_knowledge_rating=0.2,
                    user_estimated_knowledge_rating=0.2,
                    importance=0.6,
                    relevance=0.6,
                    view_frequency=1,
                    source_material_ids=[],
                    embedding=[0.1] * 768,
                )
            )
            await session.commit()
            await session.execute(
                text(
                    "UPDATE nodes SET search_vector = to_tsvector('english', COALESCE(topic_name, '')) "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": "proj-suggest-q-int"},
            )
            await session.commit()

    async def drop_db():
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await engine.dispose()

    asyncio.run(init_db())

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(
        "app.services.node_suggestions.embedding_service.requests.post",
        _fake_gemini_post,
    )
    monkeypatch.setattr(
        "app.services.node_suggestions.keyword_extraction_service.requests.post",
        _fake_gemini_post,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/questions/suggestions/raw-text",
                json={
                    "project_id": "proj-suggest-q-int",
                    "text": "Graph search explores nodes and edges efficiently.",
                    "threshold": 0.7,
                    "semantic_weight": 0.6,
                    "keyword_weight": 0.4,
                    "top_k": 20,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert "strong" in payload
            assert "weak" in payload
            suggestions = payload["strong"] + payload["weak"]
            assert len(suggestions) > 0
            assert any(item.get("suggestion_type") in {"EXISTING", "NEW"} for item in suggestions)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(drop_db())
