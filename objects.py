"""
objects.py

Defines the database objects.
"""

import os
import xml.etree.ElementTree as ET
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from base import Base, session


class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    text = Column(String)

    questions = relationship("Question", order_by="Question.id", backref="hw")

    def from_xml(self, filename):
        self.name = os.path.splitext(os.path.basename(filename))[0]
        tree = ET.parse(filename)
        root = tree.getroot()
        for q in root.iter('question'):
            q_object = Question.from_xml(q)
            q_object.hw = self
            session.add(q_object)
            session.commit()


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    hw_id = Column(Integer, ForeignKey('hws.id'))
    points = Column(Integer)
    type = Column(String)

    __mapper_args__ = {'polymorphic_on': type,
                       'polymorphic_identity': 'question'}

    @staticmethod
    def from_xml(node):
        """Constructs a Question object from an xml node"""

        if node.attrib['type'] == 'Multiple Choice':
            q = MultipleChoiceQuestion()
        elif node.attrib['type'] == 'Long Answer':
            q = LongAnswerQuestion()
        elif node.attrib['type'] == 'Short Answer':
            q = ShortAnswerQuestion()
        else:
            raise ValueError

        q.from_xml(node)
        q.points = int(node.attrib['points'])
        return q

    def score(self, answer):
        pass


class MultipleChoiceQuestion(Question):
    __mapper_args__ = {'polymorphic_identity': 'Multiple Choice'}
    options = relationship("MultipleChoiceOption",
                           order_by="MultipleChoiceOption.id",
                           backref="question")

    def from_xml(self, node):
        for i, option in enumerate(node.find('options').findall('option')):
            text = option.text
            correct = option.attrib['correct']
            option_object = MultipleChoiceOption(order=i,
                                                 text=text,
                                                 correct=correct,
                                                 question=self)
            session.add(option_object)
            session.commit()


class MultipleChoiceOption(Base):
    __tablename__ = 'mc_options'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    order = Column(Integer)
    text = Column(String)
    correct = Column(Integer)


class ShortAnswerQuestion(Question):
    __mapper_args__ = {'polymorphic_identity': 'Short Answer'}

    def from_xml(self, node):
        pass


class LongAnswerQuestion(Question):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def from_xml(self, node):
        pass
