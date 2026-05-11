from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, Session
from ..database import Base, generate_id

class Argument(Base):
    __tablename__ = 'arguments'

    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False)
    source_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    V_active = Column(Float, default=1.0)
    V_initial = Column(Float, default=1.0)
    inverion_triggered = Column(Boolean, default=False)
    root_fallacy_id = Column(String, nullable=True)
    bypass_count = Column(Integer, default=0)
    bypass_lockout_until = Column(DateTime, nullable=True)
    collapse_timestamp = Column(DateTime, nullable=True)

    claims = relationship("Claim", back_populates="argument")
    edges = relationship("ClaimEdge", back_populates="argument")
    veracity_events = relationship("VeracityEvent", back_populates="argument")

class Claim(Base):
    __tablename__ = 'claims'

    id = Column(String, primary_key=True, default=generate_id)
    argument_id = Column(String, ForeignKey('arguments.id'), nullable=False)
    text = Column(Text, nullable=False)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    position_z = Column(Float, nullable=True)
    is_conclusion = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    argument = relationship("Argument", back_populates="claims")
    fallacies = relationship("Fallacy", back_populates="claim")

class Fallacy(Base):
    __tablename__ = 'fallacies'

    id = Column(String, primary_key=True, default=generate_id)
    claim_id = Column(String, ForeignKey('claims.id'), nullable=False)
    fallacy_type = Column(String, nullable=False)
    magnitude = Column(Float, default=0.5)
    persistence = Column(Float, default=0.5)
    parent_fallacy_id = Column(String, ForeignKey('fallacies.id'), nullable=True)
    depth = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="fallacies")

class ClaimEdge(Base):
    __tablename__ = 'claim_edges'

    id = Column(String, primary_key=True, default=generate_id)
    argument_id = Column(String, ForeignKey('arguments.id'), nullable=False)
    source_claim_id = Column(String, ForeignKey('claims.id'), nullable=False)
    target_claim_id = Column(String, ForeignKey('claims.id'), nullable=False)
    logical_strength = Column(Float, default=1.0)

    argument = relationship("Argument", back_populates="edges")

class VeracityEvent(Base):
    __tablename__ = 'veracity_events'

    id = Column(String, primary_key=True, default=generate_id)
    argument_id = Column(String, ForeignKey('arguments.id'), nullable=False)
    tick_index = Column(Integer, nullable=True)
    V_before = Column(Float, nullable=True)
    V_after = Column(Float, nullable=True)
    V_cost = Column(Float, nullable=True)
    fallacy_id = Column(String, ForeignKey('fallacies.id'), nullable=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    argument = relationship("Argument", back_populates="veracity_events")

class ManifoldSnapshot(Base):
    __tablename__ = 'manifold_snapshots'

    id = Column(String, primary_key=True, default=generate_id)
    argument_id = Column(String, ForeignKey('arguments.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    integrity_score = Column(Float, nullable=True)
    mesh_vertices_json = Column(Text, nullable=True)
    fallacies_json = Column(Text, nullable=True)