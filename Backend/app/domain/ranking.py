"""
Phase 6: Question Ranking & Selection Engine

Scores weak concept clusters and questions to select the best next question
for a user to answer based on their knowledge state.
"""

import heapq
from datetime import datetime
from typing import Optional

from .clustering import Cluster
from .user_knowledge import UserNodeState
from .question import Question
from .question_bank import QuestionBank


# ============================================================
# CLUSTER SCORING
# ============================================================


def score_cluster(
    cluster: Cluster,
    user_node_states: dict[str, UserNodeState],
    now: datetime,
    importance_lookup: dict[str, float]
) -> float:
    """Score a cluster based on weakness of its nodes.
    
    Higher scores indicate clusters that need more attention.
    Score combines maximum weakness and average weakness.
    
    Args:
        cluster: Cluster to score
        user_node_states: Mapping of node_id to UserNodeState
        now: Current timestamp for forgetting calculations
        importance_lookup: Node importance values
    
    Returns:
        Cluster score (>= 0), higher is more urgent
    """
    if not cluster.node_ids:
        return 0.0
    
    weakness_scores = []
    
    for node_id in cluster.node_ids:
        # Get user state for this node (may not exist)
        state = user_node_states.get(node_id)
        if state is None:
            # No state means never reviewed - maximum weakness
            weakness = 1.0
        else:
            # Calculate weakness using importance
            importance = importance_lookup.get(node_id, 1.0)
            weakness = state.weakness_score(now=now, importance=importance)
        
        weakness_scores.append(weakness)
    
    # Combine max and average for score
    # Max captures urgent nodes, average captures overall cluster weakness
    max_weakness = max(weakness_scores)
    avg_weakness = sum(weakness_scores) / len(weakness_scores)
    
    # Weight max more heavily (70/30 split)
    cluster_score = 0.7 * max_weakness + 0.3 * avg_weakness
    
    return cluster_score


# ============================================================
# REDUNDANCY PENALTY
# ============================================================


def compute_redundancy_penalty(
    question: Question,
    recently_attempted_question_ids: set[str]
) -> float:
    """Compute penalty for recently attempted questions.
    
    Questions that were recently attempted receive a penalty
    to encourage variety in question selection.
    
    Args:
        question: Question to check
        recently_attempted_question_ids: Set of recently attempted question IDs
    
    Returns:
        Penalty value (>= 0), higher means more redundant
    """
    if question.id in recently_attempted_question_ids:
        # Fixed penalty for recently attempted questions
        return 0.5
    else:
        # No penalty for fresh questions
        return 0.0


# ============================================================
# QUESTION SCORING
# ============================================================


def score_question(
    question: Question,
    cluster_score: float,
    redundancy_penalty: float
) -> float:
    """Score a question based on cluster importance and redundancy.
    
    Higher scores indicate better questions to ask next.
    
    Args:
        question: Question to score
        cluster_score: Score of the cluster this question covers
        redundancy_penalty: Penalty for recent attempts
    
    Returns:
        Question score, higher is better
    """
    # Base score from cluster urgency
    base_score = cluster_score
    
    # Amplify with question importance
    importance_multiplier = 1.0 + (question.metadata.importance / 10.0)
    score_with_importance = base_score * importance_multiplier
    
    # Apply redundancy penalty
    final_score = score_with_importance - redundancy_penalty
    
    # Ensure non-negative
    return max(0.0, final_score)


# ============================================================
# RANKING ENGINE
# ============================================================


class QuestionRankingEngine:
    """Selects the best next question using heap-based ranking.
    
    Scores clusters and questions to deterministically select
    the highest-value question for a user to answer.
    """
    
    @staticmethod
    def select_next_question(
        clusters: list[Cluster],
        question_bank: QuestionBank,
        user_node_states: dict[str, UserNodeState],
        importance_lookup: dict[str, float],
        recently_attempted_question_ids: set[str],
        now: datetime
    ) -> Optional[Question]:
        """Select the best next question using heap-based ranking.
        
        Algorithm:
        1. Score each cluster
        2. Find questions covering each cluster
        3. Score each question with cluster score and redundancy penalty
        4. Use max-heap to select highest-scoring question
        5. Deterministic tie-breaking by question ID
        
        Args:
            clusters: List of weak node clusters
            question_bank: Question repository
            user_node_states: User's knowledge states
            importance_lookup: Node importance values
            recently_attempted_question_ids: Recently answered questions
            now: Current timestamp
        
        Returns:
            Highest-scoring question, or None if no valid questions
        """
        if not clusters:
            return None
        
        # Max-heap (use negative scores since heapq is min-heap)
        heap = []
        
        for cluster in clusters:
            # Score this cluster
            cluster_score = score_cluster(
                cluster,
                user_node_states,
                now,
                importance_lookup
            )
            
            # Find questions covering this cluster's nodes
            candidate_questions = QuestionRankingEngine._find_questions_for_cluster(
                cluster,
                question_bank
            )
            
            # Score each candidate question
            for question in candidate_questions:
                redundancy_penalty = compute_redundancy_penalty(
                    question,
                    recently_attempted_question_ids
                )
                
                question_score = score_question(
                    question,
                    cluster_score,
                    redundancy_penalty
                )
                
                # Push onto max-heap (negate score for max-heap behavior)
                # Tie-breaker: use question ID for determinism
                heap_entry = (
                    -question_score,  # Negative for max-heap
                    question.id,      # Deterministic tie-breaker
                    question
                )
                heapq.heappush(heap, heap_entry)
        
        # Return highest-scoring question
        if heap:
            _, _, best_question = heapq.heappop(heap)
            return best_question
        
        return None
    
    @staticmethod
    def _find_questions_for_cluster(
        cluster: Cluster,
        question_bank: QuestionBank
    ) -> list[Question]:
        """Find questions that cover nodes in the cluster.
        
        Args:
            cluster: Cluster to find questions for
            question_bank: Question repository
        
        Returns:
            List of questions covering cluster nodes
        """
        questions_found = {}  # Use dict with id as key to deduplicate
        
        # For each node in cluster, find questions covering it
        for node_id in cluster.node_ids:
            node_questions = question_bank.get_questions_by_node(node_id)
            for question in node_questions:
                questions_found[question.id] = question
        
        return list(questions_found.values())
