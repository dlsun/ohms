"""
objects.py

Defines the database objects.
"""

import os
import xml.etree.ElementTree as ET
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from base import Base, session


class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

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
    xml = Column(String)

    items = relationship("Item", order_by="Item.id", backref="question")

    @staticmethod
    def from_xml(node):
        question = Question()
        for item in node.iter('item'):
            item_object = Item.from_xml(item)
            item_object.question = question
            session.add(item_object)
            session.commit()
        
        question.xml = ET.tostring(node)
        return question


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    points = Column(Integer)
    type = Column(String)

    __mapper_args__ = {'polymorphic_on': type,
                       'polymorphic_identity': 'item'}

    @staticmethod
    def from_xml(node):
        """Constructs a Item object from an xml node"""

        if node.attrib['type'] == 'Multiple Choice':
            item = MultipleChoiceItem()
        elif node.attrib['type'] == 'Long Answer':
            item = LongAnswerItem()
        elif node.attrib['type'] == 'Short Answer':
            item = ShortAnswerItem()
        else:
            raise ValueError

        item.from_xml(node)
        item.points = int(node.attrib['points'])
        return item

    def score(self, answer):
        pass


class MultipleChoiceItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Multiple Choice'}
    options = relationship("MultipleChoiceOption",
                           order_by="MultipleChoiceOption.id",
                           backref="item")

    def from_xml(self, node):
        for i, option in enumerate(node.find('options').findall('option')):
            text = option.text
            correct = option.attrib['correct']
            option_object = MultipleChoiceOption(order=i,
                                                 text=text,
                                                 correct=correct,
                                                 item=self)
            session.add(option_object)
            session.commit()


class MultipleChoiceOption(Base):
    __tablename__ = 'mc_options'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'))
    order = Column(Integer)
    text = Column(String)
    correct = Column(Integer)


class ShortAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Short Answer'}

    def from_xml(self, node):
        pass


class LongAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def from_xml(self, node):
        pass


class Student(Base):
    __tablename__ = 'students'
    sunet = Column(String, primary_key=True)
    name = Column(String)


class Answer(Base):
    __tablename__ = 'answers'

    # Unused fields will be set to null
    id = Column(Integer, primary_key=True)
    sunet = Column(String, ForeignKey('students.sunet'))
    item_id = Column(Integer, ForeignKey('items.id'))
    option_id = Column(Integer, ForeignKey('mc_options.id'))
    time = Column(DateTime)
    text = Column(String)
    real = Column(Float)
    integral = Column(Integer)
