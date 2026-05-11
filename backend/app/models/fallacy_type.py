from sqlalchemy import Column, String, Float, Text
from ..database import Base

class FallacyType(Base):
    __tablename__ = 'fallacy_types'

    name = Column(String, primary_key=True)
    category = Column(String, nullable=True)
    base_weight = Column(Float, default=0.5)
    visual_form = Column(String, nullable=True)
    description = Column(Text, nullable=True)