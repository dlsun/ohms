"""
homework.py

Defines the homework objects.
"""

import os
import xml.etree.ElementTree as ET
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from server import Base, session
import question


class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    text = Column(String)

    questions = relationship("question.Question", order_by="Question.id", backref="hw")

    def from_xml(self, filename):
        self.name = os.path.splitext(os.path.basename(filename))[0]
        tree = ET.parse(filename)
        root = tree.getroot()
        for q in root.iter('question'):
            q_object = question.from_xml(q)
            q_object.hw = self
            session.add(q_object)
            session.commit()
