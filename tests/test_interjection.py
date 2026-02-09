"""
Phase 10: Active Interjection & Revision Planning Tests
"""

from datetime import datetime, timedelta

import pytest

from backend.app.domain import (
    ContentSession,
    InterjectionPolicy,
    InterjectionEngine,
    RevisionPlanner,
    Graph,
    Node,
    Edge,
    EdgeType,
    Question,
    QuestionMetadata,
    QuestionType,
    KnowledgeType,
    QuestionBank,
    UserNodeState,
    WeakNodeDetector,
    WeakNodeClusterer,
    QuestionRankingEngine,
)


def create_node(node_id: str, material_id: str | None = None, importance: float = 1.0) -> Node:
    node = Node(id=node_id, project_id="test_project_1", topic_name=node_id.capitalize(), importance=importance)
    if material_id:
        node.source_material_ids.add(material_id)
    return node


def create_question(question_id: str, covered: list[str]) -> Question:
    metadata = QuestionMetadata(
        created_by="test",
        created_at=datetime.now(),
        importance=1.0,
    )
    return Question(
        id=question_id,
        project_id="test_project_1",
        text=f"Question {question_id}",
        answer="Answer",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=covered,
        metadata=metadata,
    )


def create_state(node_id: str, pkr: float, last_reviewed: datetime) -> UserNodeState:
    return UserNodeState(
        user_id="user1",
        node_id=node_id,
        project_id="test_project_1",
        proven_knowledge_rating=pkr,
        stability=5.0,
        last_reviewed_at=last_reviewed,
    )


# ============================================================
# CONTENT SESSION & POLICY
# ============================================================


class TestContentSession:
    def test_valid_content_session_creation(self):
        now = datetime.now()
        session = ContentSession(
            session_id="sess1",
            material_id="mat1",
            user_id="user1",
            project_id="test_project_1",
            started_at=now,
            last_interjection_at=None,
            consumed_chunks=0,
        )
        assert session.session_id == "sess1"
        assert session.material_id == "mat1"
        assert session.user_id == "user1"
        assert session.started_at == now
        assert session.last_interjection_at is None
        assert session.consumed_chunks == 0

    def test_consumed_chunks_increments_correctly(self):
        now = datetime.now()
        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=0,
        )
        session.increment_consumed_chunks()
        session.increment_consumed_chunks(2)
        assert session.consumed_chunks == 3

    def test_last_interjection_at_updates_correctly(self):
        now = datetime.now()
        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=0,
        )
        interject_time = now + timedelta(minutes=5)
        session.record_interjection(interject_time)
        assert session.last_interjection_at == interject_time


class TestInterjectionPolicy:
    def test_interjects_by_chunk_count(self):
        now = datetime.now()
        session = ContentSession(
            session_id="sess1",
            material_id="mat1",
            user_id="user1",
            project_id="test_project_1",
            started_at=now,
            last_interjection_at=None,
            consumed_chunks=5,
        )
        policy = InterjectionPolicy(min_chunks_between_interjections=3, max_time_without_interjection=timedelta(minutes=10))
        assert policy.should_interject(session, now) is True

    def test_interjects_by_time_elapsed(self):
        start = datetime.now()
        now = start + timedelta(minutes=20)
        session = ContentSession(
            session_id="sess1",
            material_id="mat1",
            user_id="user1",
            project_id="test_project_1",
            started_at=start,
            last_interjection_at=None,
            consumed_chunks=0,
        )
        policy = InterjectionPolicy(min_chunks_between_interjections=10, max_time_without_interjection=timedelta(minutes=10))
        assert policy.should_interject(session, now) is True

    def test_no_interjection_when_below_thresholds(self):
        start = datetime.now()
        now = start + timedelta(minutes=2)
        session = ContentSession(
            session_id="sess1",
            material_id="mat1",
            user_id="user1",
            project_id="test_project_1",
            started_at=start,
            last_interjection_at=None,
            consumed_chunks=1,
        )
        policy = InterjectionPolicy(min_chunks_between_interjections=3, max_time_without_interjection=timedelta(minutes=10))
        assert policy.should_interject(session, now) is False

    def test_policy_is_deterministic(self):
        start = datetime.now()
        now = start + timedelta(minutes=11)
        session = ContentSession(
            session_id="sess1",
            material_id="mat1",
            user_id="user1",
            project_id="test_project_1",
            started_at=start,
            consumed_chunks=0,
        )
        policy = InterjectionPolicy(min_chunks_between_interjections=5, max_time_without_interjection=timedelta(minutes=10))
        assert policy.should_interject(session, now) is True
        assert policy.should_interject(session, now) is True


# ============================================================
# INTERJECTION ENGINE
# ============================================================


class TestInterjectionEngine:
    def test_returns_question_for_material_nodes(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a", material_id="mat1"))
        graph.add_node(create_node("b", material_id="mat1"))
        graph.add_edge(Edge(from_node_id="a", to_node_id="b", project_id="test_project_1", type=EdgeType.PREREQUISITE, weight=1.0))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "a": create_state("a", pkr=0.2, last_reviewed=old),
            "b": create_state("b", pkr=0.2, last_reviewed=old),
        }

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=3,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}

        question = engine.get_interjection_question(
            content_session=session,
            user_node_states=user_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert question is not None
        assert question.id == "q1"

    def test_returns_none_when_no_material_nodes(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a", material_id=None))

        bank = QuestionBank()
        now = datetime.now()

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=3,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        question = engine.get_interjection_question(
            content_session=session,
            user_node_states={},
            importance_lookup={},
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert question is None

    def test_returns_none_when_no_interjection_needed(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a", material_id="mat1"))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        user_states = {
            "a": create_state("a", pkr=0.95, last_reviewed=now),
        }

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=0,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        importance_lookup = {"a": 1.0}

        question = engine.get_interjection_question(
            content_session=session,
            user_node_states=user_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert question is None

    def test_reuses_ranking_engine_correctly(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a", material_id="mat1"))
        graph.add_node(create_node("b", material_id="mat1"))
        graph.add_edge(Edge(from_node_id="a", to_node_id="b", project_id="test_project_1", type=EdgeType.PREREQUISITE, weight=1.0))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        q2 = create_question("q2", ["b"])
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)

        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "a": create_state("a", pkr=0.2, last_reviewed=old),
            "b": create_state("b", pkr=0.2, last_reviewed=old),
        }

        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(user_states.values()),
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )
        clusterer = WeakNodeClusterer(graph=graph, max_hops=2, allowed_edge_types=None)
        clusters = clusterer.generate_clusters(weak_nodes)

        direct = QuestionRankingEngine.select_next_question(
            clusters=clusters,
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=3,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        via_engine = engine.get_interjection_question(
            content_session=session,
            user_node_states=user_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert direct is not None
        assert via_engine is not None
        assert direct.id == via_engine.id

    def test_returns_none_when_no_weak_nodes(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a", material_id="mat1"))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        user_states = {
            "a": create_state("a", pkr=0.95, last_reviewed=now),
        }

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=3,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        importance_lookup = {"a": 1.0}

        question = engine.get_interjection_question(
            content_session=session,
            user_node_states=user_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert question is None


# ============================================================
# REVISION PLANNER
# ============================================================


class TestRevisionPlanner:
    def test_generates_plan_for_weak_nodes(self):
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "weak": create_state("weak", pkr=0.2, last_reviewed=old),
            "strong": create_state("strong", pkr=0.95, last_reviewed=now),
        }

        planner = RevisionPlanner(weakness_threshold=0.4)
        plan = planner.generate_revision_plan(user_states, now, horizon=timedelta(days=7))

        assert len(plan) == 1
        assert plan[0]["node_id"] == "weak"
        assert now <= plan[0]["scheduled_time"] <= now + timedelta(days=7)

    def test_reason_is_high_forgetting_or_low_pkr(self):
        now = datetime.now()
        old = now - timedelta(days=60)
        user_states = {
            "forgetting": create_state("forgetting", pkr=0.8, last_reviewed=old),
            "lowpkr": create_state("lowpkr", pkr=0.2, last_reviewed=now),
        }

        planner = RevisionPlanner(weakness_threshold=0.4)
        plan = planner.generate_revision_plan(user_states, now, horizon=timedelta(days=7))

        reasons = {item["node_id"]: item["reason"] for item in plan}
        assert reasons["forgetting"] == "high forgetting"
        assert reasons["lowpkr"] == "low PKR"

    def test_deterministic_ordering(self):
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "b": create_state("b", pkr=0.2, last_reviewed=old),
            "a": create_state("a", pkr=0.2, last_reviewed=old),
        }

        planner = RevisionPlanner(weakness_threshold=0.5)
        plan = planner.generate_revision_plan(user_states, now, horizon=timedelta(days=7))

        assert plan[0]["node_id"] == "a"
        assert plan[1]["node_id"] == "b"

    def test_empty_plan_when_no_weak_nodes(self):
        now = datetime.now()
        user_states = {
            "strong": create_state("strong", pkr=0.95, last_reviewed=now),
        }

        planner = RevisionPlanner(weakness_threshold=0.5)
        plan = planner.generate_revision_plan(user_states, now, horizon=timedelta(days=7))
        assert plan == []


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestInterjectionIntegration:
    def test_full_flow_interjection(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("x", material_id="mat1"))
        graph.add_node(create_node("y", material_id="mat1"))
        graph.add_edge(Edge(from_node_id="x", to_node_id="y", project_id="test_project_1", type=EdgeType.PREREQUISITE, weight=1.0))

        bank = QuestionBank()
        q1 = create_question("q1", ["x"])
        q2 = create_question("q2", ["y"])
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)

        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "x": create_state("x", pkr=0.2, last_reviewed=old),
            "y": create_state("y", pkr=0.2, last_reviewed=old),
        }

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=5,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}

        question = engine.get_interjection_question(
            content_session=session,
            user_node_states=user_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert question is not None
        assert question.id in {"q1", "q2"}

        # Answer and continue
        question.record_attempt(success=True, timestamp=now)
        for node_id in question.covered_node_ids:
            if node_id in user_states:
                user_states[node_id].record_success(now)

        session.record_interjection(now)
        session.increment_consumed_chunks(1)

        policy = InterjectionPolicy(min_chunks_between_interjections=10, max_time_without_interjection=timedelta(minutes=10))
        assert policy.should_interject(session, now + timedelta(minutes=1)) is False

        planner = RevisionPlanner(weakness_threshold=0.5)
        plan = planner.generate_revision_plan(user_states, now + timedelta(minutes=1), horizon=timedelta(days=7))
        assert isinstance(plan, list)

    def test_multiple_users_same_material(self):
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("x", material_id="mat1"))
        graph.add_node(create_node("y", material_id="mat1"))
        graph.add_edge(Edge(from_node_id="x", to_node_id="y", project_id="test_project_1", type=EdgeType.PREREQUISITE, weight=1.0))

        bank = QuestionBank()
        q1 = create_question("q1", ["x"])
        bank.add_question(q1, graph)

        now = datetime.now()
        old = now - timedelta(days=30)

        user1_states = {
            "x": create_state("x", pkr=0.2, last_reviewed=old),
            "y": create_state("y", pkr=0.2, last_reviewed=old),
        }
        user2_states = {
            "x": create_state("x", pkr=0.9, last_reviewed=now),
            "y": create_state("y", pkr=0.9, last_reviewed=now),
        }

        session = ContentSession(session_id="sess1", material_id="mat1", user_id="user1", project_id="test_project_1",
            started_at=now,
            consumed_chunks=5,
        )

        engine = InterjectionEngine(graph, bank, QuestionRankingEngine)
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}

        q_user1 = engine.get_interjection_question(
            content_session=session,
            user_node_states=user1_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )
        q_user2 = engine.get_interjection_question(
            content_session=session,
            user_node_states=user2_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=set(),
            now=now,
        )

        assert q_user1 is not None
        assert q_user2 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])