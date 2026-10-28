"""
tests/test_state.py
────────────────────
Tests for the VEXION state machine.
"""

import pytest
from app.core.state import AppState, StateManager


@pytest.fixture
def sm():
    return StateManager()


class TestInitialState:
    def test_starts_idle(self, sm):
        assert sm.state == AppState.IDLE

    def test_label_is_ready(self, sm):
        assert sm.label == "READY"


class TestValidTransitions:
    def test_idle_to_listening(self, sm):
        assert sm.transition(AppState.LISTENING)
        assert sm.state == AppState.LISTENING

    def test_idle_to_thinking(self, sm):
        assert sm.transition(AppState.THINKING)

    def test_listening_to_thinking(self, sm):
        sm.transition(AppState.LISTENING)
        assert sm.transition(AppState.THINKING)

    def test_thinking_to_speaking(self, sm):
        sm.transition(AppState.THINKING)
        assert sm.transition(AppState.SPEAKING)

    def test_thinking_to_executing(self, sm):
        sm.transition(AppState.THINKING)
        assert sm.transition(AppState.EXECUTING)

    def test_thinking_to_needs_approval(self, sm):
        sm.transition(AppState.THINKING)
        assert sm.transition(AppState.NEEDS_APPROVAL)

    def test_speaking_to_idle(self, sm):
        sm.transition(AppState.THINKING)
        sm.transition(AppState.SPEAKING)
        assert sm.transition(AppState.IDLE)

    def test_executing_to_idle(self, sm):
        sm.transition(AppState.THINKING)
        sm.transition(AppState.EXECUTING)
        assert sm.transition(AppState.IDLE)


class TestInvalidTransitions:
    def test_idle_to_speaking_blocked(self, sm):
        # IDLE → SPEAKING is not a valid transition
        assert not sm.transition(AppState.SPEAKING)
        assert sm.state == AppState.IDLE   # unchanged

    def test_listening_to_executing_blocked(self, sm):
        sm.transition(AppState.LISTENING)
        assert not sm.transition(AppState.EXECUTING)

    def test_speaking_to_executing_blocked(self, sm):
        sm.transition(AppState.THINKING)
        sm.transition(AppState.SPEAKING)
        assert not sm.transition(AppState.EXECUTING)


class TestObservers:
    def test_observer_called_on_transition(self, sm):
        calls = []
        sm.add_observer(lambda s, t: calls.append((s, t)))
        sm.transition(AppState.LISTENING)
        assert len(calls) == 1
        assert calls[0][0] == AppState.LISTENING

    def test_multiple_observers(self, sm):
        a, b = [], []
        sm.add_observer(lambda s, t: a.append(s))
        sm.add_observer(lambda s, t: b.append(s))
        sm.transition(AppState.THINKING)
        assert a and b

    def test_bad_observer_does_not_crash(self, sm):
        sm.add_observer(lambda s, t: 1 / 0)   # raises ZeroDivisionError
        # Should not propagate
        sm.transition(AppState.THINKING)
        assert sm.state == AppState.THINKING


class TestHelpers:
    def test_set_idle(self, sm):
        sm.force_transition(AppState.THINKING)
        sm.set_idle()
        assert sm.state == AppState.IDLE

    def test_is_busy_while_listening(self, sm):
        sm.transition(AppState.LISTENING)
        assert sm.is_busy()

    def test_not_busy_while_idle(self, sm):
        assert not sm.is_busy()

    def test_set_executing_with_label(self, sm):
        sm.force_transition(AppState.THINKING)
        sm.set_executing("Opening VS Code")
        assert sm.state == AppState.EXECUTING
        assert "Opening VS Code" in sm.status_text

    def test_set_error(self, sm):
        sm.set_error("Something broke")
        assert sm.state == AppState.ERROR
        assert "Something broke" in sm.status_text
