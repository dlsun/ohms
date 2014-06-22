"""
objects.py

Defines the database objects.
"""

from __future__ import division
import elementtree.ElementTree as ET
import re
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UnicodeText
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.session import make_transient
from base import Base, session
from datetime import datetime, timedelta
from pdt import pdt_now

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

    @staticmethod
    def from_xml(node):
        hw = Homework(name=node.attrib['name'])
        if 'start_date' in node.attrib:
            hw.start_date = datetime.strptime(node.attrib['start_date'],
                                                "%m/%d/%Y %H:%M:%S")
        else:
            hw.start_date = None
        if 'due_date' in node.attrib:
            hw.due_date = datetime.strptime(node.attrib['due_date'],
                                              "%m/%d/%Y %H:%M:%S")
        else:
            hw.due_date = None
        for i, q in enumerate(node.iter('question')):
            print 'Processing Question %d' % (i+1)
            q_object = Question.from_xml(q)
            q_object.hw = hw
            session.add(q_object)
        return hw

class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    hw_id = Column(Integer, ForeignKey('hws.id'))
    type = Column(String(20))
    xml = Column(UnicodeText)
    items = relationship("Item", order_by="Item.id", backref="question")
    points = Column(Float)

    homework = relationship("Homework")

    __mapper_args__ = {'polymorphic_identity': 'question',
                       'polymorphic_on': type}

    @staticmethod
    def from_xml(node):
        # if question already has ID assigned, fetch instance; otherwise create new
        if 'id' in node.attrib:
            question = session.query(Question).get(node.attrib['id'])
            question.points = 0
        else:
            if 'type' in node.attrib and node.attrib['type'] == 'peer_review':
                question = PeerReview()
                question.points = float(node.attrib['points'])
            else:
                question = Question()
                question.points = 0
            session.add(question)
            session.flush()
            node.attrib['id'] = str(question.id)
        # question properties
        question.name = node.attrib['name'] if 'name' in node.attrib else ""
        question.items = []
        # iterate over items
        for e in node.iter():
            if e.tag == "item":
                # save the tail
                tail = strip_and_save_tail(e)
                # fetch item object
                item = Item.from_xml(e)
                # add item to question
                question.points += float(item.points)
                question.items.append(item)
                # update the item with its ID, re-append the tail
                e.attrib['id'] = str(item.id)
                e.tail = tail

        question.xml = ET.tostring(node, method="xml")
        session.commit()

        return question

    def to_html(self, include_items=True):

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
                        if include_items: parent.insert(j, e_new)
                        break
                i += 1
        return ET.tostring(node, method="html")

    def __iter__(self):
        """Iterates over the items in this question, in order"""
        for item in self.items:
            yield item

    def __str__(self):
        return self.to_html()

    def check_if_locked(self, last_submission):
        due_date = self.homework.due_date
        return due_date and due_date < pdt_now()

    def delay_feedback(self, submission):
        if submission is None or submission.score is None:
            return submission
        due_date = submission.question.homework.due_date
        submission.item_responses # instantiate item responses before we detach object from session
        make_transient(submission) # detaches SQLAlchemy object from session
        now = pdt_now()
        time_available = min(submission.time + timedelta(minutes=30), due_date)
        if now < time_available:
            submission.score = None
            submission.comments = '''Feedback on your submission will be available in %s minutes, at %s. Please refresh the page at that time to view it.''' % (1 + (time_available - now).seconds // 60, time_available.strftime("%H:%M"))
        return submission

    def load_response(self, stuid):
        from queries import get_last_question_response
        last_submission = get_last_question_response(self.id, stuid)
        out = {
            'submission': self.delay_feedback(last_submission),
            'locked': self.check_if_locked(last_submission),
            }
        if pdt_now() > self.homework.due_date:
            out['solution'] = [item.solution for item in self.items]
        return out

    def submit_response(self, stuid, responses):
        from queries import get_last_question_response
        last_submission = get_last_question_response(self.id, stuid)
        if not self.check_if_locked(last_submission):
            item_responses = [ItemResponse(item_id=item.id, response=response) \
                                  for item, response in zip(self.items, responses)]
            score, comments = self.check(responses)
            question_response = QuestionResponse(
                stuid=stuid,
                time=pdt_now(),
                question_id=self.id,
                item_responses=item_responses,
                score=score,
                comments=comments
                )
            session.add(question_response)
            session.commit()
            return {
                'submission': self.delay_feedback(question_response),
                'locked': self.check_if_locked(question_response),
            }
        else:
            raise Exception("The deadline for submitting this homework has passed.")

    def check(self, responses):
        scores, comments = zip(*[item.check(response) for (item, response)
                                 in zip(self, responses)])
        if any(s is None for s in scores):
            return None, "Feedback for this submission will not be available until after a peer or an instructor has reviewed it."
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

        klass_map = {'Multiple Choice': MultipleChoiceItem,
                     'Long Answer': LongAnswerItem,
                     'Short Answer': ShortAnswerItem}
        if node.attrib['type'] in klass_map:
            klass = klass_map[node.attrib['type']]
        else:
            raise ValueError('type of question not recognized, options are %s' % `klass_map.keys()`)

        # get existing item based on ID, if specified
        if 'id' in node.attrib:
            item = session.query(Item).get(node.attrib['id'])
        # otherwise create new item
        else:
            item = klass()
            session.add(item)

        item.sync_from_node(node)
        item.xml = ET.tostring(node, method="xml")
        session.flush()
        return item

    def to_html(self):
        return ET.Element("p")

    def check(self, response):
        return None, ""
       
    def sync_from_node(self, node):
        """
        Abstract method.

        Set appropriate attributes of `self` from `node.attrib`.

        Called during instance creation through `Item.from_xml` constructor,
        also typically called in `Item.to_html` when 
        the instance may have been loaded from database and not
        have all pythonic attributes set because they were not stored
        in the database.
        """
        raise NotImplementedError

class MultipleChoiceItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Multiple Choice'}

    def sync_from_node(self, node):
        """
        Set appropriate attributes of `self` from `node.attrib`.
        """
        self.points = float(node.attrib['points'])
        self.options = []
        solutions = []
        for i, option in enumerate(node.iter('option')):
            option_obj = Option(option.text)
            if 'correct' in option.attrib and option.attrib['correct'].lower() == "true":
                option_obj.points = self.points
                solutions.append(str(i))
            else:
                option_obj.points = float(option.attrib['points']) if 'points' in option.attrib else 0
            for comment in option.findall('comment'):
                option_obj.comment = comment.text
            self.options.append(option_obj)
        self.solution = ", ".join(solutions)

    def to_html(self):

        self.sync_from_node(ET.fromstring(self.xml))

        attrib = {"class": "item",
                  "itemtype": "multiple-choice"}
        root = ET.Element("div", attrib=attrib)
        for i, option in enumerate(self.options):
            node = ET.fromstring(r'''
<p><input type='radio' name='%d' value='%d' disabled='disabled'></input></p>
''' % (self.id, i))
            node[0].text = " " + str(option)
            root.append(node)

        return root

    def check(self, response):

        # parse the answers from the XML
        self.sync_from_node(ET.fromstring(self.xml))

        try:
            option = self.options[int(response)]
            return option.points, option.comment
        except:
            raise Exception("Invalid multiple choice answer.")

class Option:
    points = None
    comment = ""

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class ShortAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Short Answer'}

    def sync_from_node(self, node):
        """
        Set appropriate attributes of `self` from `node.attrib`.
        """
        self.points = float(node.attrib['points'])
        self.answers = []
        solutions = []
        for answer_node in node.findall("answer"):
            answer = ShortAnswer(answer_node)
            answer.points = answer.points or self.points # this seems like the
                                                         # xml is probably not quite correct?
            if answer.type in ["exact", "expression"]:
                solutions.append(answer.exact)
            self.answers.append(answer)
        if not solutions:
            solutions.append(str(0.5*(answer.lb + answer.ub)))
        self.solution = ", ".join(solutions)

    def to_html(self):

        # parse the answers from the XML
        self.sync_from_node(ET.fromstring(self.xml))

        # set attributes of textbox
        size = "medium" if any(a.type == "expression" for a in self.answers) else "mini"
        attrib = {"type": "text",
                  "itemtype": "short-answer",
                  "disabled": "disabled",
                  "class": "item input-%s" % size
                  }

        return ET.Element("input", attrib=attrib)

    def check(self, response):

        # parse the answers from the XML
        self.from_xml(ET.fromstring(self.xml))

        # check the answer
        for answer in self.answers:
            if answer.is_correct(response):
                return answer.points, answer.comment
        return 0, ""

class ShortAnswer(object):

    def __init__(self, node):
        if 'points' in node.attrib:
            self.points = float(a.attrib['points'])
        else:
            self.points = None 

        self.type = node.attrib['type'].lower()
        self.comment = ""
        for comment in node.findall('comment'):
            self.comment += comment.text
        data = node.text
        if self.type == "range": # why have the range as list in a string -- why not upper and lower?
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
            response = "".join([c for c in response if c in '1234567890.-'])
            try:
                num_response = float(response)
            except ValueError:
                raise Exception("I didn't understand your response. Please try again.")
            return self.lb - 1e-10 <= num_response <= self.ub + 1e-10
        elif self.type == "exact":
            str_response = response.strip().lower()
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
            raise Exception("Answer type not supported.")
        return False

class LongAnswerItem(Item):
    __mapper_args__ = {'polymorphic_identity': 'Long Answer'}

    def sync_from_node(self, node):
        """
        Set appropriate attributes of `self` from `node.attrib`.
        """
        self.points = float(node.attrib['points'])
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
    stuid = Column(String(10), primary_key=True)
    name = Column(String(100))
    type = Column(String(10))
    proxy = Column(String(10)) # allows admin to be a proxy for another user


class QuestionResponse(Base):
    __tablename__ = 'question_responses'
    id = Column(Integer, primary_key=True)
    stuid = Column(String(10), ForeignKey('users.stuid'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    question = relationship("Question")
    time = Column(DateTime)
    item_responses = relationship("ItemResponse",
                                  order_by="ItemResponse.id",
                                  backref="question")
    score = Column(Float)
    comments = Column(UnicodeText)
    sample = Column(Integer)

    user = relationship("User")

    def __str__(self):
        return "\n\n".join(ir.response for ir in self.item_responses)


class ItemResponse(Base):
    __tablename__ = 'item_responses'
    id = Column(Integer, primary_key=True)
    question_response_id = Column(Integer, ForeignKey('question_responses.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    response = Column(UnicodeText)

    question_response = relationship("QuestionResponse")
    item_response = relationship("Item")    


class GradingTask(Base):
    __tablename__ = 'grading_tasks'
    id = Column(Integer, primary_key=True)
    grader = Column(String(10), ForeignKey('users.stuid'))
    student = Column(String(10), ForeignKey('users.stuid'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    time = Column(DateTime)
    score = Column(Float)
    comments = Column(UnicodeText)
    rating = Column(Integer)

    question = relationship("Question")


class PeerReview(Question):
    __mapper_args__ = {'polymorphic_identity': 'Peer Review'}

    def set_metadata(self):
        node = ET.fromstring(self.xml)
        self.question_id = int(node.attrib['question_id'])
        self.points = float(node.attrib['points'])

    def to_html(self):

        # not good to have imports here...
        from queries import get_question, get_last_question_response, get_peer_tasks_for_grader, get_self_tasks_for_student 
        from auth import validate_user

        self.set_metadata()

        user = validate_user()
        question = get_question(self.question_id)

        peer_tasks = get_peer_tasks_for_grader(self.question_id, user.stuid)
        self_tasks = get_self_tasks_for_student(self.question_id, user.stuid)

        self_reflection = True if self_tasks else False
        peer_question_responses = [get_last_question_response(self.question_id, task.student) for task in peer_tasks]
        self_question_response = get_last_question_response(self.question_id, user.stuid) if self_tasks else None

        # jinja2 stuff
        from jinja2 import Environment, PackageLoader
        env = Environment(autoescape=True, loader=PackageLoader("ohms", "templates"))
        template = env.get_template("peer_review_question.html")

        return template.render(question=question, 
                        peer_question_responses=peer_question_responses,
                        self_reflection=self_reflection,
                        self_question_response=self_question_response
                        )

    def load_response(self, stuid):

        from queries import get_peer_tasks_for_grader, get_self_tasks_for_student
        self.set_metadata()
        
        # get peer and self assessment tasks
        tasks = get_peer_tasks_for_grader(self.question_id, stuid)
        tasks.extend(get_self_tasks_for_student(self.question_id, stuid))

        # get grading tasks
        item_responses = []
        ratings = []
        time = None
        score = 0
        for task in tasks:
            item_responses.append({"response": task.score})
            item_responses.append({"response": task.comments})
            if task.rating is not None: ratings.append(task.rating)
            if task.comments is not None: score += self.points / len(tasks)
            time = task.time

        # provide some feedback to grader if at least 2 students have rated feedback
        if len(ratings) > 1:
            median = sorted(ratings)[len(ratings) // 2]
            comment = "%d peers responded to your feedback. " % len(ratings)
            if median == 4:
                comment += "They were satisfied overall with the quality of your feedback."
            elif median == 3:
                comment += "Your feedback was good, but some peers felt that it could have been better."
            elif median <= 2:
                comment += "Your peers did not find your feedback satisfactory. If you are concerned, please see a member of the course staff to discuss strategies to improve."
        elif score:
            comment = "Your peers have not had the chance yet to look over their feedback. When they do, their feedback will be shown here."
        else:
            comment = ""

        return {
            "locked": (pdt_now() > self.homework.due_date),
            "submission": { 
                "item_responses": item_responses,
                "score": score,
                "comments": comment,
                "time": time
            }
        }

    def submit_response(self, stuid, responses):

        from queries import get_peer_tasks_for_grader, get_self_tasks_for_student
        self.set_metadata()

        if pdt_now() <= self.homework.due_date:

            # get peer and self assessment tasks
            tasks = get_peer_tasks_for_grader(self.question_id, stuid)
            tasks.extend(get_self_tasks_for_student(self.question_id, stuid))

            i = 0
            score = 0
            item_responses = []
            while i < len(responses):
                task = tasks[i // 2]
                if task.grader != stuid:
                    raise Exception("You are not authorized to grade this response.")
                try:
                    assert(0 <= float(responses[i]) <= task.question.points)
                except:
                    raise Exception("Please enter a score between %f and %f." % (0, task.question.points))
                if not responses[i+1].strip():
                    raise Exception("Please enter comments for all responses.")

                item_responses.append({"response": task.score})
                item_responses.append({"response": task.comments})
                task.time = pdt_now()
                task.score = responses[i]
                task.comments = responses[i+1]

                if task.comments is not None: score += self.points / len(tasks)

                i += 2
            session.commit()
            
            return {
                'locked': (pdt_now() > self.homework.due_date),
                'submission': {
                    "time": pdt_now(),
                    "score": score,
                    "comments": '''You've earned credit for completing the peer reviews, but your peer review grade will also depend on the accuracy and quality of your feedback.''',
                    "item_responses": item_responses
                    }
            }
        else:
            raise Exception("The deadline for submitting this homework has passed.")


class Grade(Base):
    __tablename__ = 'grades'

    student = Column(String(10), primary_key=True)
    assignment = Column(String(50), primary_key=True)
    time = Column(DateTime)
    score = Column(Float)
    points = Column(Float)
