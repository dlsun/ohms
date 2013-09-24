#!/usr/bin/python
"""
OHMS: Online Homework Management System
"""

from jinja2 import Environment, FileSystemLoader, StrictUndefined
env = Environment(loader=FileSystemLoader("templates"),
                  autoescape=True,
                  undefined=StrictUndefined)

from sqlalchemy.orm.query import Query
import json
import cgi
from datetime import datetime

from base import session
from objects import Homework, Question, Item, QuestionResponse, ItemResponse
from objects import GradingTask, QuestionGrade, GradingPermission
from queries import get_question_responses, get_question_grades

import os
sunet = os.environ.get("WEBAUTH_LDAP_USER") or "dlsun"


application_json = "Content-Type: application/json\n\n"
text_html = "Content-Type: text/html\n\n"


# special JSON encoder to handle dates and Response objects
class NewEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return datetime.strftime(obj, "%m/%d/%Y %H:%M:%S")
        elif isinstance(obj, QuestionResponse):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            d['item_responses'] = obj.item_responses
            return d
        elif isinstance(obj, ItemResponse):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            return d
        elif isinstance(obj, QuestionGrade):
            d = {}
            for column in obj.__table__.columns:
                d[column.name] = getattr(obj, column.name)
            d['item_responses'] = [
                {"response": obj.score},
                {"response": obj.comments}
                ]
            return d
        return json.JSONEncoder.default(self, obj)


def index():
    hws = session.query(Homework).all()
    print text_html + env.get_template("index.html").render(homeworks=hws)


def hw():
    form = cgi.FieldStorage()
    hw_id = form["id"].value
    homework = session.query(Homework).filter_by(id=hw_id).one()
    print text_html + env.get_template("hw.html").render(homework=homework)


def grade():
    form = cgi.FieldStorage()
    hw_id = form["id"].value
    permissions = session.query(GradingPermission).\
        filter_by(sunet=sunet).join(Question).\
        filter(Question.hw_id == hw_id).all()
    questions = []
    for permission in permissions:
        question = permission.question
        if permission.permissions:
            tasks = session.query(GradingTask).\
                filter_by(grader=sunet).join(QuestionResponse).\
                filter(QuestionResponse.question_id == question.id).all()
        else:
            qrs = session.query(QuestionResponse).\
                filter_by(sunet="Sample Sam").\
                filter_by(question_id=question.id).all()
            tasks = [{"id": qr.id,
                      "question_response":qr} for qr in qrs]
        questions.append({
                "question": question, 
                "permission": permission.permissions,
                "tasks": tasks})
    print text_html +\
        env.get_template("grade.html").render(questions=questions)


def load():
    form = cgi.FieldStorage()
    q_id = form["q_id"].value
    if q_id[0] == "q":
        last_submission = get_question_responses(q_id[1:], sunet)
    elif q_id[0] == "g":
        last_submission = get_question_grades(q_id[1:], sunet)
    else:
        last_submission = None
    if last_submission:
        return application_json +\
            json.dumps({"last_submission": last_submission[0]}, cls=NewEncoder)
    else:
        return application_json + json.dumps({})


def submit():
    form = cgi.FieldStorage()
    q_id = form["q_id"].value
    type = q_id[0]
    id = q_id[1:]

    # TODO: FIXME! (this will fail)
    responses = request.form.getlist('responses')

    question_response = QuestionResponse(
        sunet=sunet,
        time=datetime.now(),
        question_id=id
        )

    if type == "q":

        question = session.query(Question).filter_by(id=id).one()

        past_responses = get_question_responses(id, sunet)
        items = session.query(Item).filter_by(question_id=id).all()

        score, comments = question.check(responses)

        question_response.score = score
        question_response.comments = comments
        for item, response in zip(items, responses):
            item_response = ItemResponse(item_id=item.id, response=response)
            question_response.item_responses.append(item_response)

        # add response to the database
        session.add(question_response)
        session.commit()

    else:

        if type == "s":

            sample_responses = session.query(QuestionResponse).\
                filter_by(sunet="Sample Sam").\
                filter_by(question_id=id).all()

            assigned_scores = [float(response) for response in responses]
            true_scores = [float(response.score) for response in sample_responses]

            if assigned_scores == true_scores:
                session.query(GradingPermission).\
                    filter_by(sunet=sunet).\
                    filter_by(question_id=id).\
                    update({"permissions":1})
                session.commit()
                question_response.comments = r'''
Congratulations! You are now qualified to grade this question. 
Please refresh the page to see the student responses.'''
            else:
                question_response.comments = r'''
Sorry, but there is still a discrepancy between your grades 
and the grades for this sample response. Please try again.'''
            
        elif type == "g":

            task = session.query(GradingTask).get(id)
            score = float(responses[0])
            comments = responses[1]

            question_grade = QuestionGrade(
                grading_task=task,
                time=datetime.now(),
                score=score,
                comments=comments
                )
            session.add(question_grade)
            session.commit()

            question_response.comments = r'''Your scores have 
been successfully recorded!'''

    # add response to what to return to the user
    return application_json +\
        json.dumps({"last_submission": question_response}, cls=NewEncoder)


def route():
    form = cgi.FieldStorage()

    try:
        dest = form['dest'].value
    except KeyError:
        # TODO: throw error
        pass

    try:
        handler = {'index': index,
                   'hw': hw,
                   'grade': grade,
                   'load': load,
                   'submit': submit}[dest]
    except KeyError:
        # TODO: throw error
        pass

    handler()

if __name__ == "__main__":
    route()
