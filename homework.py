"""
homework.py

Defines the homework objects.
"""

import xml.etree.ElementTree as ET
from sqlalchemy import Column, Integer, String, ForeignKey
from server import Base, session
import question


class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    text = Column(String)

    def from_xml(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        for q in root.iter('question'):
            q_object = question.from_xml(q)
            q_object.hw_id = self.id
            session.add(q_object)
            session.commit()
