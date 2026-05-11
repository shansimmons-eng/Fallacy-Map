from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..models import Argument, VeracityEvent

class VeracityAuditor:
    def __init__(self, db: Session, argument_id: str):
        self.db = db
        self.argument_id = argument_id
        self.V_c = 1.0
        self.V_active = 1.0
        self.previous_V_active = 1.0
        self.spike_threshold = 0.5
        self.bypass_lockout_duration = 3.0
        self.bypass_lockout_until: Optional[datetime] = None
        self.tick_index = 0
        self._load_state()

    def _load_state(self):
        arg = self.db.query(Argument).filter(Argument.id == self.argument_id).first()
        if arg:
            self.V_active = arg.V_active
            self.V_c = arg.V_initial
            self.previous_V_active = self.V_active

    def _save_state(self):
        arg = self.db.query(Argument).filter(Argument.id == self.argument_id).first()
        if arg:
            arg.V_active = self.V_active
            if self.V_active <= 0 and not arg.inverion_triggered:
                arg.inverion_triggered = True
                arg.collapse_timestamp = datetime.utcnow()
            self.db.commit()

    def is_bypass_locked(self) -> bool:
        if self.bypass_lockout_until and datetime.utcnow() < self.bypass_lockout_until:
            return True
        self.bypass_lockout_until = None
        return False

    def process_fallacy(self, fallacy_type: str, magnitude: float, persistence: float,
                       claim_id: str, parent_fallacy_id: Optional[str] = None) -> Dict[str, Any]:
        self.tick_index += 1
        self.previous_V_active = self.V_active

        if self.is_bypass_locked():
            return {
                "accepted": False,
                "reason": "bypass_lockout",
                "V_active": self.V_active,
                "V_cost": 0
            }

        V_cost = magnitude * persistence
        self.V_active -= V_cost

        delta = self.previous_V_active - self.V_active

        result = {
            "accepted": True,
            "V_cost": V_cost,
            "V_before": self.previous_V_active,
            "V_after": self.V_active,
            "delta": delta,
            "bypass_triggered": False,
            "inverion_triggered": False,
            "tick_index": self.tick_index
        }

        if delta > self.spike_threshold:
            result["bypass_triggered"] = True
            self.bypass_lockout_until = datetime.utcnow() + timedelta(seconds=self.bypass_lockout_duration)
            self._record_event("bypass", V_cost, None)
            self._increment_bypass_count()
        else:
            self._record_event("fallacy", V_cost, None)

        if self.V_active <= 0:
            result["inverion_triggered"] = True
            self.V_active = 0
            self._record_event("divide", 0, None)

        self._save_state()
        return result

    def _record_event(self, event_type: str, V_cost: float, fallacy_id: Optional[str]):
        event = VeracityEvent(
            argument_id=self.argument_id,
            tick_index=self.tick_index,
            V_before=self.previous_V_active,
            V_after=self.V_active,
            V_cost=V_cost,
            fallacy_id=fallacy_id,
            event_type=event_type
        )
        self.db.add(event)
        self.db.commit()

    def _increment_bypass_count(self):
        arg = self.db.query(Argument).filter(Argument.id == self.argument_id).first()
        if arg:
            arg.bypass_count += 1
            self.db.commit()

    def set_root_fallacy(self, fallacy_id: str):
        arg = self.db.query(Argument).filter(Argument.id == self.argument_id).first()
        if arg and arg.inverion_triggered and not arg.root_fallacy_id:
            arg.root_fallacy_id = fallacy_id
            self.db.commit()

    def get_state(self) -> Dict[str, Any]:
        return {
            "V_c": self.V_c,
            "V_active": self.V_active,
            "spike_threshold": self.spike_threshold,
            "bypass_locked": self.is_bypass_locked(),
            "inverion_triggered": self.V_active <= 0,
            "tick_index": self.tick_index
        }