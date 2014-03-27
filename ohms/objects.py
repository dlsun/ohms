"""
objects.py

Defines the database objects.
"""

from __future__ import division
import os
import elementtree.ElementTree as ET
import re
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UnicodeText
from sqlalchemy.orm import relationship, backref
from base import Base, session
from datetime import datetime


# helper function that strips tail from element and returns tail
def strip_and_save_tail(element):
    tail = element.tail
    element.tail = None
    return tail


class Homework(Base):
    __tablename__ = 'hws'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
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
        for i, q in enumerate(root.iter('question')):
            print 'Processing Question %d' % (i+1)
            q_object = Question.from_xml(q)
            q_object.hw = self
            session.add(q_object)


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    hw_id = Column(Integer, ForeignKey('hws.id'))
    xml = Column(UnicodeText)
    items = relationship("Item", order_by="Item.id", backref="question")
    points = Column(Float)

    homework = relationship("Homework")

    @staticmethod
    def from_xml(node):
        # if question already has ID assigned, fetch instance; otherwise create new
        if 'id' in node.attrib:
            question = session.query(Question).get(node.attrib['id'])
        else:
            question = Question()
            session.add(question)
            session.flush()
            node.attrib['id'] = str(question.id)
        # question properties
        question.name = node.attrib['name'] if 'name' in node.attrib else ""
        question.points = 0
        question.items = []
        # iterate over items
        for e in node.iter():
            if e.tag == "item":
                # save the tail
                tail = strip_and_save_tail(e)
                # fetch item object
                item = Item.from_xml(e)
                # add item to question
                question.points += item.points
                question.items.append(item)
                # update the item with its ID, re-append the tail
                e.attrib['id'] = str(item.id)
                e.tail = tail

        question.xml = ET.tostring(node, method="xml")
        session.commit()

        return question

    def to_html(self):
        node = ET.fromstring(self.xml)
        parent_map = dict((c, p) for p in node.iter() for c in p)
        i = 0
        for e in node.iter():
            # replace item by HTML
            if e.tag == "item":
                e_new = self.items[i].to_html()
                e_new.tail = e.tail
                parent = parent_map[e]
                for j, child in enumerate(parent):
                    if child == e:
                        parent.remove(e)
                        parent.insert(j, e_new)
                        break
                i += 1
        return ET.tostring(node, method="html")

    def __iter__(self):
        """Iterates over the items in this question, in order"""
        for item in self.items:
            yield item

    def __str__(self):
        return self.to_html()

    def check(self, responses):
        scores, comments = zip(*[item.check(response) for (item, response)
                                 in zip(self, responses)])
        if any(s is None for s in scores):
            return None, "The score for this submission is pending, awaiting a human grader."
        else:
            return sum(scores), "<br/>".join(c for c in comments if c)


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    points = Column(Float)
    type = Column(String(20))
    xml = Column(UnicodeText)
    solution = Column(UnicodeText)

    __mapper_args__ = {'polymorphic_on': type,
                       'polymorphic_identity': 'item'}

    @staticmethod
    def from_xml(node):
        """Constructs a Item object from an xml node"""

        # gets existing Item from ID, if specified
        if 'id' in node.attrib:
            return session.query(Item).get(node.attrib['id'])

        # otherwise create new Item
        if node.attrib['type'] == 'Multiple Choice':
            item = MultipleChoiceItem()
        elif node.attrib['type'] == 'Long Answer':
            item = LongAnswerItem()
        elif node.attrib['type'] == 'Short Answer':
            item = ShortAnswerItem()
        else:
            raise ValueError

        item.from_xml(node)
        item.xml = ET.tostring(node)
        item.points = float(node.attrib['points'])
        session.add(item)
        session.flush()
        return item

    def to_html(self):
        return ET.Element("p")

    def check(self, response):
        return None, ""


class MultipleChoiceItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Multiple Choice'}

    def from_xml(self, node):

        self.options = []
        self.solution = None
        for i, option in enumerate(node.iter('option')):
            match = re.match("<option.*?>(?P<inner>.*)</option>",
                             ET.tostring(option), re.DOTALL)
            self.options.append( match.group('inner') if match else "" )
            if 'correct' in option.attrib:
                if option.attrib['correct'].lower() == "true":
                    self.solution = i

    def to_html(self):
        attrib = {"class": "item",
                  "itemtype": "multiple-choice"}
        root = ET.Element("div", attrib=attrib)

        node = ET.fromstring(self.xml)
        self.from_xml(node)
        for i, option in enumerate(self.options):
            root.append(ET.fromstring(r'''
<p><input type='radio' name='%d' value='%d' disabled='disabled'> %s</input></p>
                ''' % (self.id, i, option)))

        return root

    def check(self, response):
        if response == self.solution:
            return self.points, ""
        elif self.solution is None:
            return self.points, ""
        else:
            return 0, ""


class ShortAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Short Answer'}
    answers = relationship("ShortAnswer", backref="item")

    def from_xml(self, node):
        short_answer = None
        solutions = []
        for answer in node.findall("answer"):
            short_answer = ShortAnswer()
            short_answer.from_xml(answer)
            short_answer.item = self
            session.add(short_answer)
            if short_answer.type in ["exact", "expression"]:
                solutions.append(short_answer.exact)
        if not solutions:
            solutions.append(str(0.5*(short_answer.lb + short_answer.ub)))
        self.solution = ", ".join(solutions)

    def to_html(self):
        attrib = {"type": "text",
                  "itemtype": "short-answer",
                  "disabled": "disabled"}
        size = "medium"
        for answer in self.answers:
            if answer.type == "range" or answer.exact.isdigit():
                size = "mini"
        attrib['class'] = "item input-%s" % size
        return ET.Element("input", attrib=attrib)

    def check(self, response):
        for answer in self.answers:
            if answer.is_correct(response):
                return self.points, ""
        return 0, ""

# TODO: make this a regular object, not tied to database
class ShortAnswer(Base):
    __tablename__ = "short_answers"

    id = Column(Integer, primary_key=True)
    short_answer_id = Column(Integer, ForeignKey('items.id'))
    type = Column(String(10))  # "range" or "exact" or "expression"
    lb = Column(Float)
    ub = Column(Float)
    exact = Column(String(100))

    def from_xml(self, node):
        self.type = node.attrib['type'].lower()
        data = node.text
        if self.type == "range":
            lb, ub = data.split(",")
            self.lb = float(lb.strip().lstrip("["))
            self.ub = float(ub.strip().rstrip("]"))
        elif self.type == "exact" or self.type == "expression":
            self.exact = data.strip().lower()
        else:
            raise NotImplementedError("ShortAnswer type=%s is not implemented"
                                      % self.type)        

    @staticmethod
    def validate(expr):
        if expr.count("(") != expr.count(")"):
            raise Exception("You have mismatched parentheses (...) in your expression.")
        allowed_chars = [str(n) for n in range(10)]
        allowed_chars.extend([".", "+", "-", "*", "/", "(", ")"])
        diff = set(expr)-set(allowed_chars)
        if diff:
            non_ascii = [c for c in diff if ord(c)>=128]
            if non_ascii:
                raise Exception('''The character %s is not an ASCII character. Perhaps you copied and pasted from Microsoft Word, or have confused it with a similar character?''' % non_ascii[0])
            else:
                raise Exception("You have the following illegal characters in your expression: %s" % ", ".join(diff))
        return True

    @staticmethod
    def preprocess(expr):
        # remove all whitespace
        expr = "".join(expr.split())
        # replace x with *
        expr = expr.replace("x", "*")
        # replace ^ with **
        expr = expr.replace("^", "**")
        # convert parentheses to explicit multiplications
        expr = expr.replace(")(", ")*(")
        for i in range(10):
            expr = expr.replace("%d(" % i, "%d*(" % i)
        return expr

    def is_correct(self, response):
        if self.type == "range":
            try:
                num_response = float(response)
            except ValueError:
                return False
            return self.lb - 1e-10 <= num_response <= self.ub + 1e-10
        elif self.type == "exact":
            str_response = response.strip().lower()
            # TODO: make this an edit distance comparison
            return str_response == self.exact
        elif self.type == "expression":
            if response:
                processed_response = self.preprocess(response)
                self.validate(processed_response)
                ans = eval(self.preprocess(self.exact), {"__builtins__": None})
                try:
                    resp = eval(processed_response, {"__builtins__": None})
                except:
                    raise Exception("I'm sorry, but I did not understand the expression you typed in. Please check the expression and try again.")
                return abs(resp - ans) < 1e-15 
            else:
                return False
        else:
            raise NotImplementedError("ShortAnswer type=%s is not implemented"
                                      % self.type)


class LongAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def from_xml(self, node):
        solution = node.find('solution')
        self.solution = ET.tostring(solution) if solution is not None else ""

    def to_html(self):
        attrib = {"class": "item span7",
                  "itemtype": "long-answer",
                  "rows": "4",
                  "disabled": "disabled"}
        node = ET.Element("textarea", attrib=attrib)
        return node


class User(Base):
    __tablename__ = 'users'
    sunet = Column(String(10), primary_key=True)
    name = Column(String(100))
    type = Column(String(10))
    group = Column(Integer)


class QuestionResponse(Base):
    __tablename__ = 'question_responses'
    id = Column(Integer, primary_key=True)
    sunet = Column(String(10), ForeignKey('users.sunet'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    question = relationship("Question")
    time = Column(DateTime)
    item_responses = relationship("ItemResponse",
                                  order_by="ItemResponse.id",
                                  backref="question")
    score = Column(Float)
    comments = Column(UnicodeText)
    sample = Column(Integer)

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
    response = Column(UnicodeText)

    question_response = relationship("QuestionResponse")
    item_response = relationship("Item")    


class GradingPermission(Base):
    __tablename__ = "grading_permissions"
    id = Column(Integer, primary_key=True)
    sunet = Column(String(10), ForeignKey('users.sunet'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    permissions = Column(Integer)
    due_date = Column(DateTime)

    user = relationship("User")
    question = relationship("Question")


class GradingTask(Base):
    __tablename__ = 'grading_tasks'
    id = Column(Integer, primary_key=True)
    grader = Column(String(10), ForeignKey('users.sunet'))
    question_response_id = Column(Integer, ForeignKey('question_responses.id'))

    question_response = relationship("QuestionResponse")


class QuestionGrade(Base):
    __tablename__ = 'question_grades'
    id = Column(Integer, primary_key=True)
    grading_task_id = Column(Integer,
                             ForeignKey('grading_tasks.id'))
    time = Column(DateTime)
    score = Column(Float)
    comments = Column(UnicodeText)
    rating = Column(Integer)

    grading_task = relationship("GradingTask")
