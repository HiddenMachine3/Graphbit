"""Active interjection and revision planning."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field

from .graph import Graph
from .question_bank import QuestionBank
from .question import Question
from .user_knowledge import UserNodeState
from .clustering import WeakNodeDetector, WeakNodeClusterer
from .ranking import QuestionRankingEngine


# ============================================================
# CONTENT SESSION
# ============================================================


class ContentSession(BaseModel):
    """
    Tracks content consumption session for interjections.
    """

    session_id: str = Field(..., min_length=1)
    material_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    started_at: datetime
    last_interjection_at: Optional[datetime] = None
    consumed_chunks: int = Field(default=0, ge=0)

    def increment_consumed_chunks(self, count: int = 1) -> None:
        """Increment consumed content chunks."""
        if count < 0:
            raise ValueError("count must be >= 0")
        self.consumed_chunks += count

    def record_interjection(self, timestamp: datetime) -> None:
        """Record the time of an interjection."""
        self.last_interjection_at = timestamp


# ============================================================
# INTERJECTION POLICY
# ============================================================


class InterjectionPolicy:
    """
    Decides when to interject during content consumption.
    """

    def __init__(
        self,
        min_chunks_between_interjections: int,
        max_time_without_interjection: timedelta,
    ) -> None:
        if min_chunks_between_interjections < 1:
            raise ValueError("min_chunks_between_interjections must be >= 1")
        if max_time_without_interjection.total_seconds() <= 0:
            raise ValueError("max_time_without_interjection must be > 0")
        self.min_chunks_between_interjections = min_chunks_between_interjections
        self.max_time_without_interjection = max_time_without_interjection

    def should_interject(self, content_session: ContentSession, now: datetime) -> bool:
        """
        Determine whether to interject now.

        Rules:
        - Interject if consumed_chunks >= min_chunks_between_interjections
        - OR if time since last interjection (or start) exceeds max_time_without_interjection
        """
        if content_session.consumed_chunks >= self.min_chunks_between_interjections:
            return True

        last_time = content_session.last_interjection_at or content_session.started_at
        return (now - last_time) >= self.max_time_without_interjection


# ============================================================
# INTERJECTION ENGINE
# ============================================================


class InterjectionEngine:
    """
    Selects interjection questions during content consumption.
    """

    def __init__(
        self,
        graph: Graph,
        question_bank: QuestionBank,
        ranking_engine: QuestionRankingEngine,
    ) -> None:
        self.graph = graph
        self.question_bank = question_bank
        self.ranking_engine = ranking_engine

    def get_interjection_question(
        self,
        content_session: ContentSession,
        user_node_states: dict[str, UserNodeState],
        importance_lookup: dict[str, float],
        recently_attempted_question_ids: set[str],
        now: datetime,
    ) -> Optional[Question]:
        """
        Select a question for interjection.

        Behavior:
        - Identify nodes linked to the material
        - Generate clusters (Phase 5)
        - Select next question (Phase 6)
        """
        # Identify nodes linked to the material
        material_node_ids = {
            node_id
            for node_id, node in self.graph.nodes.items()
            if content_session.material_id in node.source_material_ids
        }

        if not material_node_ids:
            return None

        # Filter user states to material-linked nodes
        relevant_states = [
            state for node_id, state in user_node_states.items()
            if node_id in material_node_ids
        ]

        if not relevant_states:
            return None

        # Weak node detection
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=relevant_states,
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )

        if not weak_nodes:
            return None

        # Cluster weak nodes
        clusterer = WeakNodeClusterer(
            graph=self.graph,
            max_hops=2,
            allowed_edge_types=None,
        )
        clusters = clusterer.generate_clusters(weak_nodes)

        if not clusters:
            return None

        # Select question via Phase 6 ranking
        return self.ranking_engine.select_next_question(
            clusters=clusters,
            question_bank=self.question_bank,
            user_node_states=user_node_states,
            importance_lookup=importance_lookup,
            recently_attempted_question_ids=recently_attempted_question_ids,
            now=now,
        )


# ============================================================
# REVISION PLANNER
# ============================================================


class RevisionPlanner:
    """
    Generates future revision plans based on memory state.
    """

    def __init__(self, weakness_threshold: float = 0.5) -> None:
        if not 0.0 <= weakness_threshold <= 1.0:
            raise ValueError("weakness_threshold must be between 0.0 and 1.0")
        self.weakness_threshold = weakness_threshold

    def generate_revision_plan(
        self,
        user_node_states: dict[str, UserNodeState],
        now: datetime,
        horizon: timedelta,
    ) -> list[dict]:
        """
        Generate a deterministic revision plan within a horizon.

        Each plan item includes:
        - node_id
        - scheduled_time
        - reason
        """
        if horizon.total_seconds() <= 0:
            raise ValueError("horizon must be > 0")

        plan_items: list[dict] = []

        for node_id, state in user_node_states.items():
            weakness = state.weakness_score(now=now, importance=1.0)
            if weakness < self.weakness_threshold:
                continue

            forgetting = state.forgetting_score(now=now)
            if forgetting >= 0.5:
                reason = "high forgetting"
            elif state.proven_knowledge_rating <= 0.5:
                reason = "low PKR"
            else:
                reason = "high weakness"

            # Schedule earlier for higher weakness (deterministic)
            capped = min(max(weakness, 0.0), 1.0)
            offset_seconds = horizon.total_seconds() * (1.0 - capped)
            scheduled_time = now + timedelta(seconds=offset_seconds)

            plan_items.append({
                "node_id": node_id,
                "scheduled_time": scheduled_time,
                "reason": reason,
            })

        # Deterministic ordering: by scheduled_time then node_id
        plan_items.sort(key=lambda item: (item["scheduled_time"], item["node_id"]))

        return plan_items