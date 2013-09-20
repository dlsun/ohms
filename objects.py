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
    points = Column(Integer)

    @staticmethod
    def from_xml(node):
        question = Question()
        question.points = 0
        for i, item in enumerate(node.iter('item')):
            item_object = Item.from_xml(item)
            item_object.order = i
            question.points += item_object.points
            question.items.append(item_object)

        question.xml = ET.tostring(node)
        session.add(question)
        session.commit()

        return question

    def __iter__(self):
        """Iterates over the items in this question, in order"""
        for item in sorted(self.items, key=lambda x: x.order):
            yield item

    def to_html(self):
        body = ET.fromstring(self.xml)
        for i, item in enumerate(body.iter('item')):
            item.clear()
            item.append(self.items[i].to_html())
        return body

    def __str__(self):
        return ET.tostring(self.to_html(), method="html")

    def check(self, responses):
        scores, comments = zip(*[item.check(response) for (item, response)
                                 in zip(self, responses)])
        return sum(scores), "<br>".join(comments)


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    points = Column(Integer)
    order = Column(Integer)
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
        return 0, "%s points have yet to be graded." % self.points


class MultipleChoiceItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Multiple Choice'}
    options = relationship("MultipleChoiceOption",
                           order_by="MultipleChoiceOption.id",
                           backref="item")

    def from_xml(self, node):
        for i, option in enumerate(node.find('options').findall('option')):
            text = option.text
            correct = option.attrib['correct'].lower()
            if correct not in ["true", "false"]:
                raise ValueError("The 'correct' attribute in multiple choice"
                                 "options must be one of 'true' or 'false'")
            correct = 1 if correct == 'true' else 0
            option_object = MultipleChoiceOption(order=i,
                                                 text=text,
                                                 correct=correct,
                                                 item=self)
            session.add(option_object)
            session.commit()

    def __iter__(self):
        """Iterates over the multiple choice options in this item, in order"""
        for mc_option in sorted(self.options, key=lambda x: x.order):
            yield mc_option

    def to_html(self):
        attrib = {"class": "item",
                  "type": "multiple-choice"}
        root = ET.Element("div", attrib=attrib)

        for option in self:
            root.append(ET.fromstring(r'''
<p><input type='radio' name='%d' value='%d'> %s</input></p>
''' % (self.id, option.order, option.text)))
        return root

    def check(self, response):
        correct = [option.order for option in self if option.correct]
        if response == str(correct[0]):
            return self.points, ""
        else:
            return 0, ""


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
        attrib = {"type": "text",
                  "class": "item input-medium",
                  "type": "short-answer"}
        return ET.Element("input", attrib=attrib)


class LongAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def from_xml(self, node):
        pass

    def to_html(self):
        attrib = {"class": "item span7",
                  "type": "long-answer",
                  "rows": "4"}
        node = ET.Element("textarea", attrib=attrib)
        return node


class User(Base):
    __tablename__ = 'users'
    sunet = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)


class QuestionResponse(Base):
    __tablename__ = 'question_responses'
    id = Column(Integer, primary_key=True)
    sunet = Column(String, ForeignKey('users.sunet'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    time = Column(DateTime)
    item_responses = relationship("ItemResponse",
                                  order_by="ItemResponse.id",
                                  backref="question")
    score = Column(Float)
    comments = Column(String)


class ItemResponse(Base):
    __tablename__ = 'item_responses'
    id = Column(Integer, primary_key=True)
    question_response_id = Column(Integer, ForeignKey('question_responses.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    response = Column(String)


class GradingAssignment(Base):
    __tablename__ = 'grading_assignments'
    id = Column(Integer, primary_key=True)
    grader = Column(String, ForeignKey('users.sunet'))
    question_response_id = Column(Integer, ForeignKey('question_responses.id'))
    due_date = Column(DateTime)


class GradedQuestionResponse(Base):
    __tablename__ = 'graded_question_responses'
    id = Column(Integer, primary_key=True)
    grading_assignment_id = Column(Integer,
                                   ForeignKey('grading_assignments.id'))
    # Note: Make sure to check grading authorization before allowing people
    # to submit a grade, (ie, check that they were actually assigned to grade
    # whatever they claim to be grading
    time = Column(DateTime)
    comments = Column(String)
    score = Column(Float)


class GradingPermission(Base):
    __tablename__ = "grading_permissions"
    id = Column(Integer, primary_key=True)
    sunet = Column(String, ForeignKey('users.sunet'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    permissions = Column(String)

    user = relationship("User")
    question = relationship("Question")
