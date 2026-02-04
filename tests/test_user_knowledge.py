"""
Phase 3: User Knowledge State & Forgetting Model Tests

Comprehensive unit tests for user-node state tracking and forgetting curves.
"""

from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from src.models import (
    UserNodeState,
    SUCCESS_PKR_GAIN,
    SUCCESS_STABILITY_GAIN,
    FAILURE_PKR_LOSS,
    FAILURE_STABILITY_LOSS,
    MIN_STABILITY,
    MAX_STABILITY,
)


# ============================================================
# USER NODE STATE CREATION TESTS
# ============================================================


class TestUserNodeStateCreation:
    """Tests for UserNodeState model creation and validation."""
    
    def test_create_valid_user_node_state(self):
        """Should create state with valid data."""
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.5,
            review_count=3,
            last_reviewed_at=datetime.now(),
            stability=2.5,
        )
        
        assert state.user_id == "user1"
        assert state.node_id == "node1"
        assert state.proven_knowledge_rating == 0.5
        assert state.review_count == 3
        assert state.last_reviewed_at is not None
        assert state.stability == 2.5
    
    def test_create_with_defaults(self):
        """Should create state with default values."""
        state = UserNodeState(user_id="user1", node_id="node1")
        
        assert state.proven_knowledge_rating == 0.0
        assert state.review_count == 0
        assert state.last_reviewed_at is None
        assert state.stability == 1.0
    
    def test_user_id_cannot_be_empty(self):
        """Should reject empty user_id."""
        with pytest.raises(ValidationError):
            UserNodeState(user_id="", node_id="node1")
    
    def test_node_id_cannot_be_empty(self):
        """Should reject empty node_id."""
        with pytest.raises(ValidationError):
            UserNodeState(user_id="user1", node_id="")
    
    def test_pkr_must_be_in_range(self):
        """Should reject PKR outside [0, 1]."""
        with pytest.raises(ValidationError):
            UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=1.5)
        
        with pytest.raises(ValidationError):
            UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=-0.1)
    
    def test_review_count_cannot_be_negative(self):
        """Should reject negative review_count."""
        with pytest.raises(ValidationError):
            UserNodeState(user_id="user1", node_id="node1", review_count=-1)
    
    def test_stability_must_be_positive(self):
        """Should reject non-positive stability."""
        with pytest.raises(ValidationError):
            UserNodeState(user_id="user1", node_id="node1", stability=0)
        
        with pytest.raises(ValidationError):
            UserNodeState(user_id="user1", node_id="node1", stability=-1.5)


# ============================================================
# REVIEW UPDATE TESTS
# ============================================================


class TestReviewUpdates:
    """Tests for recording review successes and failures."""
    
    def test_record_success_increases_pkr(self):
        """Should increase PKR on success."""
        state = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.5)
        original_pkr = state.proven_knowledge_rating
        
        state.record_success(datetime.now())
        
        assert state.proven_knowledge_rating > original_pkr
        assert state.proven_knowledge_rating <= 1.0
    
    def test_record_success_increases_stability(self):
        """Should increase stability on success."""
        state = UserNodeState(user_id="user1", node_id="node1", stability=2.0)
        original_stability = state.stability
        
        state.record_success(datetime.now())
        
        assert state.stability > original_stability
        assert state.stability <= MAX_STABILITY
    
    def test_record_success_increments_review_count(self):
        """Should increment review count on success."""
        state = UserNodeState(user_id="user1", node_id="node1", review_count=5)
        
        state.record_success(datetime.now())
        
        assert state.review_count == 6
    
    def test_record_success_updates_timestamp(self):
        """Should update last_reviewed_at on success."""
        state = UserNodeState(user_id="user1", node_id="node1")
        timestamp = datetime.now()
        
        state.record_success(timestamp)
        
        assert state.last_reviewed_at == timestamp
    
    def test_record_success_respects_pkr_ceiling(self):
        """Should not exceed PKR of 1.0."""
        state = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.99)
        
        state.record_success(datetime.now())
        
        assert state.proven_knowledge_rating <= 1.0
    
    def test_record_success_diminishing_returns(self):
        """Should have diminishing returns on PKR as it approaches 1.0."""
        state1 = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.2)
        state2 = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.8)
        
        pkr1_before = state1.proven_knowledge_rating
        pkr2_before = state2.proven_knowledge_rating
        
        state1.record_success(datetime.now())
        state2.record_success(datetime.now())
        
        gain1 = state1.proven_knowledge_rating - pkr1_before
        gain2 = state2.proven_knowledge_rating - pkr2_before
        
        # Higher PKR should gain less
        assert gain1 > gain2
    
    def test_record_success_respects_stability_ceiling(self):
        """Should not exceed max stability."""
        state = UserNodeState(user_id="user1", node_id="node1", stability=MAX_STABILITY - 0.1)
        
        state.record_success(datetime.now())
        
        assert state.stability <= MAX_STABILITY
    
    def test_record_failure_decreases_pkr(self):
        """Should decrease PKR on failure."""
        state = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.5)
        original_pkr = state.proven_knowledge_rating
        
        state.record_failure(datetime.now())
        
        assert state.proven_knowledge_rating < original_pkr
        assert state.proven_knowledge_rating >= 0.0
    
    def test_record_failure_decreases_stability(self):
        """Should decrease stability on failure."""
        state = UserNodeState(user_id="user1", node_id="node1", stability=2.0)
        original_stability = state.stability
        
        state.record_failure(datetime.now())
        
        assert state.stability < original_stability
        assert state.stability >= MIN_STABILITY
    
    def test_record_failure_increments_review_count(self):
        """Should increment review count on failure."""
        state = UserNodeState(user_id="user1", node_id="node1", review_count=5)
        
        state.record_failure(datetime.now())
        
        assert state.review_count == 6
    
    def test_record_failure_updates_timestamp(self):
        """Should update last_reviewed_at on failure."""
        state = UserNodeState(user_id="user1", node_id="node1")
        timestamp = datetime.now()
        
        state.record_failure(timestamp)
        
        assert state.last_reviewed_at == timestamp
    
    def test_record_failure_respects_pkr_floor(self):
        """Should not go below PKR of 0.0."""
        state = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.01)
        
        state.record_failure(datetime.now())
        
        assert state.proven_knowledge_rating >= 0.0
    
    def test_record_failure_respects_stability_floor(self):
        """Should not go below min stability."""
        state = UserNodeState(user_id="user1", node_id="node1", stability=MIN_STABILITY + 0.01)
        
        state.record_failure(datetime.now())
        
        assert state.stability >= MIN_STABILITY
    
    def test_multiple_successes(self):
        """Should handle multiple consecutive successes."""
        state = UserNodeState(user_id="user1", node_id="node1")
        
        for i in range(5):
            state.record_success(datetime.now() + timedelta(days=i))
        
        assert state.review_count == 5
        assert state.proven_knowledge_rating > 0.5
        assert state.stability > 1.0
    
    def test_multiple_failures(self):
        """Should handle multiple consecutive failures."""
        state = UserNodeState(user_id="user1", node_id="node1", proven_knowledge_rating=0.8)
        
        for i in range(5):
            state.record_failure(datetime.now() + timedelta(days=i))
        
        assert state.review_count == 5
        assert state.proven_knowledge_rating < 0.8
    
    def test_mixed_reviews(self):
        """Should handle mixed successes and failures."""
        state = UserNodeState(user_id="user1", node_id="node1")
        
        state.record_success(datetime.now())
        state.record_success(datetime.now() + timedelta(days=1))
        state.record_failure(datetime.now() + timedelta(days=2))
        state.record_success(datetime.now() + timedelta(days=3))
        
        assert state.review_count == 4
        assert 0.0 <= state.proven_knowledge_rating <= 1.0
        assert state.stability > 0


# ============================================================
# FORGETTING SCORE TESTS
# ============================================================


class TestForgettingScore:
    """Tests for forgetting score calculation."""
    
    def test_never_reviewed_maximum_forgetting(self):
        """Should return 1.0 if never reviewed."""
        state = UserNodeState(user_id="user1", node_id="node1")
        
        score = state.forgetting_score(datetime.now())
        
        assert score == 1.0
    
    def test_just_reviewed_minimal_forgetting(self):
        """Should return ~0.0 if just reviewed."""
        now = datetime.now()
        state = UserNodeState(user_id="user1", node_id="node1", last_reviewed_at=now)
        
        score = state.forgetting_score(now)
        
        assert score < 0.01  # Nearly zero
    
    def test_forgetting_increases_over_time(self):
        """Should increase as time passes."""
        now = datetime.now()
        state = UserNodeState(user_id="user1", node_id="node1", last_reviewed_at=now - timedelta(days=1))
        
        score_1_day = state.forgetting_score(now)
        
        state.last_reviewed_at = now - timedelta(days=7)
        score_7_days = state.forgetting_score(now)
        
        state.last_reviewed_at = now - timedelta(days=30)
        score_30_days = state.forgetting_score(now)
        
        assert score_1_day < score_7_days < score_30_days
    
    def test_higher_stability_slows_forgetting(self):
        """Should forget slower with higher stability."""
        now = datetime.now()
        review_time = now - timedelta(days=7)
        
        state_low = UserNodeState(
            user_id="user1",
            node_id="node1",
            stability=1.0,
            last_reviewed_at=review_time
        )
        
        state_high = UserNodeState(
            user_id="user1",
            node_id="node1",
            stability=5.0,
            last_reviewed_at=review_time
        )
        
        score_low = state_low.forgetting_score(now)
        score_high = state_high.forgetting_score(now)
        
        # Higher stability should result in less forgetting
        assert score_high < score_low
    
    def test_forgetting_bounded_by_one(self):
        """Should never exceed 1.0."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            stability=0.5,
            last_reviewed_at=now - timedelta(days=365)
        )
        
        score = state.forgetting_score(now)
        
        assert score <= 1.0
    
    def test_forgetting_bounded_by_zero(self):
        """Should never be negative."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            last_reviewed_at=now
        )
        
        score = state.forgetting_score(now)
        
        assert score >= 0.0
    
    def test_forgetting_deterministic(self):
        """Should return same result for same inputs."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            stability=2.0,
            last_reviewed_at=now - timedelta(days=5)
        )
        
        score1 = state.forgetting_score(now)
        score2 = state.forgetting_score(now)
        
        assert score1 == score2


# ============================================================
# WEAKNESS SCORE TESTS
# ============================================================


class TestWeaknessScore:
    """Tests for weakness score calculation."""
    
    def test_low_pkr_high_weakness(self):
        """Should have high weakness when PKR is low."""
        now = datetime.now()
        state_low = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.1,
            last_reviewed_at=now
        )
        
        state_high = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.9,
            last_reviewed_at=now
        )
        
        weakness_low = state_low.weakness_score(now, importance=5.0)
        weakness_high = state_high.weakness_score(now, importance=5.0)
        
        assert weakness_low > weakness_high
    
    def test_high_forgetting_high_weakness(self):
        """Should have high weakness when forgetting is high."""
        now = datetime.now()
        
        state_recent = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.5,
            last_reviewed_at=now - timedelta(days=1)
        )
        
        state_old = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.5,
            last_reviewed_at=now - timedelta(days=30)
        )
        
        weakness_recent = state_recent.weakness_score(now, importance=5.0)
        weakness_old = state_old.weakness_score(now, importance=5.0)
        
        assert weakness_old > weakness_recent
    
    def test_importance_amplifies_weakness(self):
        """Should have higher weakness with higher importance."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.5,
            last_reviewed_at=now - timedelta(days=7)
        )
        
        weakness_low_importance = state.weakness_score(now, importance=1.0)
        weakness_high_importance = state.weakness_score(now, importance=10.0)
        
        assert weakness_high_importance > weakness_low_importance
    
    def test_never_reviewed_high_weakness(self):
        """Should have high weakness when never reviewed."""
        now = datetime.now()
        state = UserNodeState(user_id="user1", node_id="node1")
        
        weakness = state.weakness_score(now, importance=5.0)
        
        # Should be high due to maximum forgetting and low PKR
        assert weakness > 0.5
    
    def test_well_learned_recently_low_weakness(self):
        """Should have low weakness when well-learned and recent."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.9,
            last_reviewed_at=now - timedelta(hours=1)
        )
        
        weakness = state.weakness_score(now, importance=5.0)
        
        # Should be low due to high PKR and minimal forgetting
        assert weakness < 0.3
    
    def test_weakness_deterministic(self):
        """Should return same result for same inputs."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.6,
            stability=2.0,
            last_reviewed_at=now - timedelta(days=5)
        )
        
        weakness1 = state.weakness_score(now, importance=5.0)
        weakness2 = state.weakness_score(now, importance=5.0)
        
        assert weakness1 == weakness2
    
    def test_weakness_with_zero_importance(self):
        """Should handle zero importance."""
        now = datetime.now()
        state = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.5,
            last_reviewed_at=now - timedelta(days=7)
        )
        
        weakness = state.weakness_score(now, importance=0.0)
        
        # Should still have some weakness from base components
        assert weakness > 0
    
    def test_weakness_negative_importance_error(self):
        """Should raise error for negative importance."""
        now = datetime.now()
        state = UserNodeState(user_id="user1", node_id="node1")
        
        with pytest.raises(ValueError, match="must be >= 0"):
            state.weakness_score(now, importance=-1.0)
    
    def test_weakness_combines_factors(self):
        """Should combine PKR, forgetting, and importance."""
        now = datetime.now()
        
        # Scenario 1: Low PKR, recent review, high importance
        state1 = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.2,
            last_reviewed_at=now - timedelta(days=1)
        )
        
        # Scenario 2: High PKR, old review, low importance
        state2 = UserNodeState(
            user_id="user1",
            node_id="node1",
            proven_knowledge_rating=0.8,
            last_reviewed_at=now - timedelta(days=30)
        )
        
        weakness1 = state1.weakness_score(now, importance=10.0)
        weakness2 = state2.weakness_score(now, importance=1.0)
        
        # Both should have meaningful weakness scores
        assert weakness1 > 0
        assert weakness2 > 0


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestIntegration:
    """Integration tests for realistic usage scenarios."""
    
    def test_learning_progression(self):
        """Should model realistic learning progression."""
        state = UserNodeState(user_id="user1", node_id="python_basics")
        now = datetime.now()
        
        # Initial state: never reviewed
        initial_weakness = state.weakness_score(now, importance=8.0)
        assert initial_weakness > 0.5  # High weakness
        
        # After first success
        state.record_success(now)
        after_first = state.weakness_score(now, importance=8.0)
        assert after_first < initial_weakness
        
        # After multiple successes
        for i in range(4):
            state.record_success(now + timedelta(days=i+1))
        
        well_learned = state.weakness_score(now + timedelta(days=5), importance=8.0)
        assert well_learned < after_first
        assert state.proven_knowledge_rating > 0.5
    
    def test_forgetting_and_relearning(self):
        """Should model forgetting and relearning cycle."""
        state = UserNodeState(user_id="user1", node_id="node1")
        now = datetime.now()
        
        # Learn initially
        for i in range(3):
            state.record_success(now + timedelta(days=i))
        
        pkr_after_learning = state.proven_knowledge_rating
        
        # Long break - should show high forgetting
        later = now + timedelta(days=30)
        forgetting = state.forgetting_score(later)
        assert forgetting > 0.5
        
        # Relearn - failure then success
        state.record_failure(later)
        assert state.proven_knowledge_rating < pkr_after_learning
        
        state.record_success(later + timedelta(days=1))
        # Should recover somewhat
        assert state.proven_knowledge_rating > 0
    
    def test_multiple_users_same_node(self):
        """Should track different states for different users."""
        node_id = "algorithms"
        now = datetime.now()
        
        user1_state = UserNodeState(user_id="user1", node_id=node_id)
        user2_state = UserNodeState(user_id="user2", node_id=node_id)
        
        # User 1 learns well
        for _ in range(5):
            user1_state.record_success(now)
        
        # User 2 struggles
        for _ in range(3):
            user2_state.record_failure(now)
        
        assert user1_state.proven_knowledge_rating > user2_state.proven_knowledge_rating
        assert user1_state.stability > user2_state.stability
        
        weakness1 = user1_state.weakness_score(now, importance=5.0)
        weakness2 = user2_state.weakness_score(now, importance=5.0)
        assert weakness2 > weakness1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
