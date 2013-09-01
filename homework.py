"""
homework.py

Defines the homework objects.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from server import Base


class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
