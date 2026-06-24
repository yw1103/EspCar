"""Tests for the charge state machine."""
from __future__ import annotations

from deskcar_orch.planning.charge_sm import (
    ChargeEvent,
    ChargeMachine,
    ChargeState,
    Transition,
)


def test_idle_to_seek_on_battery_low() -> None:
    sm = ChargeMachine()
    tr = sm.dispatch(ChargeEvent.BATTERY_LOW)
    assert tr == Transition(
        frm=ChargeState.IDLE,
        to=ChargeState.SEEK_DOCK,
        event=ChargeEvent.BATTERY_LOW,
    )
    assert sm.state is ChargeState.SEEK_DOCK


def test_seek_to_align_when_dock_visible() -> None:
    sm = ChargeMachine(ChargeState.SEEK_DOCK)
    tr = sm.dispatch(ChargeEvent.DOCK_VISIBLE)
    assert tr.to is ChargeState.ALIGN


def test_full_charge_cycle() -> None:
    sm = ChargeMachine()
    sm.dispatch(ChargeEvent.BATTERY_LOW)
    sm.dispatch(ChargeEvent.DOCK_VISIBLE)
    sm.dispatch(ChargeEvent.ALIGNED)
    sm.dispatch(ChargeEvent.CLOSE_ENOUGH)
    sm.dispatch(ChargeEvent.COUPLED)
    assert sm.state is ChargeState.CHARGING
    sm.dispatch(ChargeEvent.CHARGED)
    assert sm.state is ChargeState.FULL
    sm.dispatch(ChargeEvent.USER_UNDOCK)
    assert sm.state is ChargeState.UNDOCK
    sm.dispatch(ChargeEvent.CLEAR_OF_DOCK)
    assert sm.state is ChargeState.IDLE


def test_dock_lost_returns_to_seek() -> None:
    sm = ChargeMachine(ChargeState.ALIGN)
    sm.dispatch(ChargeEvent.DOCK_LOST)
    assert sm.state is ChargeState.SEEK_DOCK


def test_couple_timeout_retries_alignment() -> None:
    sm = ChargeMachine(ChargeState.COUPLE)
    sm.dispatch(ChargeEvent.COUPLE_TIMEOUT)
    assert sm.state is ChargeState.ALIGN


def test_unknown_event_does_not_change_state() -> None:
    sm = ChargeMachine(ChargeState.IDLE)
    tr = sm.dispatch(ChargeEvent.COUPLED)  # not a valid IDLE event
    assert tr.to is ChargeState.IDLE
    assert tr.frm is ChargeState.IDLE


def test_user_undock_is_wildcard() -> None:
    for s in ChargeState:
        if s is ChargeState.UNDOCK:
            continue
        sm = ChargeMachine(s)
        sm.dispatch(ChargeEvent.USER_UNDOCK)
        assert sm.state is ChargeState.UNDOCK
