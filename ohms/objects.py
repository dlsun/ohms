"""
objects.py

Defines the database objects.
"""

import os
import elementtree.ElementTree as ET
import re
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


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    hw_id = Column(Integer, ForeignKey('hws.id'))
    html = Column(String)
    items = relationship("Item", order_by="Item.id", backref="question")
    points = Column(Integer)

    @staticmethod
    def from_xml(node):
        question = Question()
        question.points = 0
        for i, item in enumerate(node.iter('item')):
            # get item object and order
            item_object = Item.from_xml(item)
            item_object.order = i
            # add items to question
            question.points += item_object.points
            question.items.append(item_object)
            # replace items by corresponding html
            item.clear()
            item.append(item_object.to_html())
        # include raw html
        question.html = ET.tostring(node, method="html")
        session.add(question)

        return question

    def __iter__(self):
        """Iterates over the items in this question, in order"""
        for item in sorted(self.items, key=lambda x: x.order):
            yield item

    def __str__(self):
        return self.html

    def check(self, responses):
        scores, comments = zip(*[item.check(response) for (item, response)
                                 in zip(self, responses)])
        return sum(scores), "<br/>".join(c for c in comments if c)


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
        item.points = float(node.attrib['points'])
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
            match = re.match("<option.*?>(?P<inner>.*)</option>", ET.tostring(option), re.DOTALL)
            text = match.group('inner') if match else ""
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
                  "itemtype": "multiple-choice"}
        root = ET.Element("div", attrib=attrib)

        for option in self:
            root.append(ET.fromstring(r'''
<p><input type='radio' name='%d' value='%d' disabled='disabled'> %s</input></p>
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
    answers = relationship("ShortAnswer", backref="item")

    def from_xml(self, node):
        for answer in node.findall("answer"):
            short_answer = ShortAnswer()
            short_answer.from_xml(answer)
            short_answer.item = self
            session.add(short_answer)

    def to_html(self):
        attrib = {"type": "text",
                  "class": "item input-medium",
                  "itemtype": "short-answer",
                  "disabled": "disabled"}
        return ET.Element("input", attrib=attrib)

    def check(self, response):
        for answer in self.answers:
            if answer.is_correct(response):
                return self.points, ""
        return 0, ""


class ShortAnswer(Base):
    __tablename__ = "short_answers"

    id = Column(Integer, primary_key=True)
    short_answer_id = Column(Integer, ForeignKey('items.id'))
    type = Column(String)  # "range" or "exact"
    lb = Column(Float)
    ub = Column(Float)
    exact = Column(String)

    def from_xml(self, node):
        self.type = node.attrib['type'].lower()
        data = node.text
        if self.type == "range":
            lb, ub = data.split(",")
            self.lb = float(lb.strip().lstrip("["))
            self.ub = float(ub.strip().rstrip("]"))
        elif self.type == "exact":
            self.exact = data.strip().lower()
        else:
            raise NotImplementedError("ShortAnswer type=%s is not implemented"
                                      % self.type)

    def is_correct(self, response):
        if self.type == "range":
            try:
                num_response = float(response)
            except ValueError:
                return False
            return self.lb <= num_response <= self.ub
        elif self.type == "exact":
            str_response = response.strip().lower()
            # TODO: make this an edit distance comparison
            return str_response == self.exact
        else:
            raise NotImplementedError("ShortAnswer type=%s is not implemented"
                                      % self.type)


class LongAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def from_xml(self, node):
        pass

    def to_html(self):
        attrib = {"class": "item span7",
                  "itemtype": "long-answer",
                  "rows": "4",
                  "disabled": "disabled"}
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

    def __str__(self):
        if len(self.item_responses) == 1:
            return self.item_responses[0].response
        else:
            return ""


class ItemResponse(Base):
    __tablename__ = 'item_responses'
    id = Column(Integer, primary_key=True)
    question_response_id = Column(Integer, ForeignKey('question_responses.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    response = Column(String)

    question_response = relationship("QuestionResponse")
    item_response = relationship("Item")


class GradingPermission(Base):
    __tablename__ = "grading_permissions"
    id = Column(Integer, primary_key=True)
    sunet = Column(String, ForeignKey('users.sunet'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    permissions = Column(Integer)
    due_date = Column(DateTime)

    user = relationship("User")
    question = relationship("Question")


class GradingTask(Base):
    __tablename__ = 'grading_tasks'
    id = Column(Integer, primary_key=True)
    grader = Column(String, ForeignKey('users.sunet'))
    question_response_id = Column(Integer, ForeignKey('question_responses.id'))

    question_response = relationship("QuestionResponse")


class QuestionGrade(Base):
    __tablename__ = 'question_grades'
    id = Column(Integer, primary_key=True)
    grading_task_id = Column(Integer,
                             ForeignKey('grading_tasks.id'))
    # Note: Make sure to check grading authorization before allowing people
    # to submit a grade, (ie, check that they were actually assigned to grade
    # whatever they claim to be grading
    time = Column(DateTime)
    comments = Column(String)
    score = Column(Float)

    grading_task = relationship("GradingTask")
