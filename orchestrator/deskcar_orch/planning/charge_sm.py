"""Charge state machine.

Pure-Python, no asyncio, no OpenCV.  The orchestrator's runtime loop
calls :meth:`ChargeMachine.dispatch` with events; the machine emits a
:class:`Transition` and the runtime applies the right controller or
driver command.

States::

    IDLE ──(battery_low)──> SEEK_DOCK
    SEEK_DOCK ──(dock_visible)──> ALIGN
    SEEK_DOCK ──(seek_timeout)──> SEEK_DOCK        (random re-roll)
    ALIGN ──(aligned)──> APPROACH
    ALIGN ──(dock_lost)──> SEEK_DOCK
    APPROACH ──(close_enough)──> COUPLE
    APPROACH ──(dock_lost)──> SEEK_DOCK
    COUPLE ──(coupled)──> CHARGING
    COUPLE ──(couple_timeout)──> ALIGN
    CHARGING ──(charged)──> FULL
    FULL ──(user_undock)──> UNDOCK
    any ──(user_undock)──> UNDOCK
    UNDOCK ──(clear_of_dock)──> IDLE
"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class ChargeState(str, enum.Enum):
    IDLE = "idle"
    SEEK_DOCK = "seek_dock"
    ALIGN = "align"
    APPROACH = "approach"
    COUPLE = "couple"
    CHARGING = "charging"
    FULL = "full"
    UNDOCK = "undock"


class ChargeEvent(str, enum.Enum):
    BATTERY_LOW = "battery_low"
    DOCK_VISIBLE = "dock_visible"
    ALIGNED = "aligned"
    CLOSE_ENOUGH = "close_enough"
    COUPLED = "coupled"
    CHARGED = "charged"
    DOCK_LOST = "dock_lost"
    COUPLE_TIMEOUT = "couple_timeout"
    SEEK_TIMEOUT = "seek_timeout"
    USER_UNDOCK = "user_undock"
    CLEAR_OF_DOCK = "clear_of_dock"


@dataclass(frozen=True)
class Transition:
    """One step of the state machine."""

    frm: ChargeState
    to: ChargeState
    event: ChargeEvent


# Transition table: (from_state, event) -> to_state.
_TRANSITIONS: dict[tuple[ChargeState, ChargeEvent], ChargeState] = {
    (ChargeState.IDLE, ChargeEvent.BATTERY_LOW): ChargeState.SEEK_DOCK,
    (ChargeState.SEEK_DOCK, ChargeEvent.DOCK_VISIBLE): ChargeState.ALIGN,
    (ChargeState.SEEK_DOCK, ChargeEvent.SEEK_TIMEOUT): ChargeState.SEEK_DOCK,
    (ChargeState.ALIGN, ChargeEvent.ALIGNED): ChargeState.APPROACH,
    (ChargeState.ALIGN, ChargeEvent.DOCK_LOST): ChargeState.SEEK_DOCK,
    (ChargeState.APPROACH, ChargeEvent.CLOSE_ENOUGH): ChargeState.COUPLE,
    (ChargeState.APPROACH, ChargeEvent.DOCK_LOST): ChargeState.SEEK_DOCK,
    (ChargeState.COUPLE, ChargeEvent.COUPLED): ChargeState.CHARGING,
    (ChargeState.COUPLE, ChargeEvent.COUPLE_TIMEOUT): ChargeState.ALIGN,
    (ChargeState.COUPLE, ChargeEvent.DOCK_LOST): ChargeState.SEEK_DOCK,
    (ChargeState.CHARGING, ChargeEvent.CHARGED): ChargeState.FULL,
    (ChargeState.FULL, ChargeEvent.USER_UNDOCK): ChargeState.UNDOCK,
    (ChargeState.UNDOCK, ChargeEvent.CLEAR_OF_DOCK): ChargeState.IDLE,
}


# ``any --(user_undock)--> UNDOCK``: install the wildcard last so a more
# specific match above wins for states that also have a UNDOCK path.
def _any_state() -> list[ChargeState]:
    return [s for s in ChargeState if s is not ChargeState.UNDOCK]


for _s in _any_state():
    _TRANSITIONS.setdefault((_s, ChargeEvent.USER_UNDOCK), ChargeState.UNDOCK)


class ChargeMachine:
    """Minimal FSM: hold a state, accept events, emit transitions."""

    def __init__(self, initial: ChargeState = ChargeState.IDLE) -> None:
        self._state = initial

    @property
    def state(self) -> ChargeState:
        return self._state

    def dispatch(self, event: ChargeEvent) -> Transition:
        key = (self._state, event)
        if key not in _TRANSITIONS:
            # Reject silently: the runtime decides how to react.
            return Transition(frm=self._state, to=self._state, event=event)
        new = _TRANSITIONS[key]
        tr = Transition(frm=self._state, to=new, event=event)
        self._state = new
        return tr

    # Convenience helpers for the runtime.
    on_enter: dict[ChargeState, Callable[[], None]] = {}
