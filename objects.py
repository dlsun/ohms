"""
objects.py

Defines the database objects.
"""

import os
import xml.etree.ElementTree as ET
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from base import Base, session
from datetime import datetime

class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    start_date = Column(DateTime)
    due_date = Column(DateTime)

    questions = relationship("Question", order_by="Question.id", backref="hw")

    def from_xml(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        self.name = root.attrib['name']
        if 'start_date' in root.attrib:
            self.start_date = datetime.strptime(root.attrib['start_date'],
                                                "%m/%d/%Y %H:%M:%S")
        else:
            self.start_date = None
        if 'due_date' in root.attrib:
            self.due_date = datetime.strptime(root.attrib['due_date'],
                                              "%m/%d/%Y %H:%M:%S")
        else:
            self.due_date = None
        for q in root.iter('question'):
            q_object = Question.from_xml(q)
            q_object.hw = self
            session.add(q_object)
            session.commit()


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    name = Column(String)
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

    def to_html(self):
        body = ET.fromstring(self.xml)
        for i, item in enumerate(body.iter('item')):
            item.clear()
            item.append(self.items[i].to_html())
        return body

    def __str__(self):
        return ET.tostring(self.to_html(), method="html")


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

    def to_html(self):
        return ET.Element("p")

    def check(self, response):
        return { "score": 0, 
                 "comments": r'''
%s points have yet to be graded.
''' % self.points}


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

    def to_html(self):
        root = ET.Element("div", attrib={
                "class": "item",
                "type": "multiple-choice"
                })
        for i, option in enumerate(self.options):
            root.append(ET.fromstring(r'''
<p><input type='radio' name='%d' value='%d'> %s</input></p>
''' % (self.id, i, option.text)))
        return root

    def check(self, response):
        correct = [i for i, option in enumerate(self.options) if option.correct=='true']
        if response == str(correct[0]):
            return {"score": self.points, "comments": ""}
        else:
            return {"score": 0, "comments": ""}


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

    def to_html(self):
        return ET.Element("input", attrib={
                "type": "text",
                "class": "item input-medium",
                "type": "short-answer"
                })


class LongAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def from_xml(self, node):
        pass

    def to_html(self):
        node = ET.Element("textarea", attrib={
                "class": "item span7",
                "type": "long-answer",
                "rows": "4"
                })
        return node


class Student(Base):
    __tablename__ = 'students'
    sunet = Column(String, primary_key=True)
    name = Column(String)


class Response(Base):
    __tablename__ = 'responses'

    # Unused fields will be set to null
    id = Column(Integer, primary_key=True)
    sunet = Column(String, ForeignKey('students.sunet'))
    item_id = Column(Integer, ForeignKey('items.id'))
    #option_id = Column(Integer, ForeignKey('mc_options.id'))
    time = Column(DateTime)
    response = Column(String)
    score = Column(Float)
    comments = Column(String)
