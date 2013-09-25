"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template, abort
import json
from datetime import datetime, timedelta

from base import session
from objects import Homework, Question, Item, QuestionResponse, ItemResponse
from objects import GradingTask, QuestionGrade, GradingPermission, User
from queries import get_question_responses, get_question_grades, exists_user
import options
app = Flask(__name__, static_url_path="")
app.debug = options.test

import os
sunet = os.environ.get("WEBAUTH_USER")
if not exists_user(sunet):
    user = User(sunet=sunet,
                name=os.environ.get("WEBAUTH_LDAP_DISPLAYNAME"),
                type="student")
    session.add(user)
    session.commit()


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


@app.route("/")
def index():
    hws = session.query(Homework).all()
    return render_template("index.html", homeworks=hws, options=options)


@app.route("/hw", methods=['GET'])
def hw():
    hw_id = request.args.get("id")
    homework = session.query(Homework).filter_by(id=hw_id).one()
    return render_template("hw.html", homework=homework, options=options)


@app.route("/grade", methods=['GET'])
def grade():
    hw_id = request.args.get("id")
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
            tasks = [{"id": qr.id, "question_response": qr} for qr in qrs]
        questions.append({
            "question": question,
            "permission": permission.permissions,
            "tasks": tasks})
    return render_template("grade.html", questions=questions, options=options)


@app.route("/load", methods=['GET'])
def load():
    q_id = request.args.get("q_id")
    if q_id[0] == "q":
        last_submission = get_question_responses(q_id[1:], sunet)
    elif q_id[0] == "g":
        last_submission = get_question_grades(q_id[1:], sunet)
    else:
        last_submission = None
    if last_submission:
        return json.dumps({"last_submission": last_submission[0]},
                          cls=NewEncoder)
    else:
        return json.dumps({})


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    submit_type = q_id[0]
    id = q_id[1:]

    responses = request.form.getlist('responses')

    question_response = QuestionResponse(
        sunet=sunet,
        time=datetime.utcnow(),
        question_id=id
    )

    # Question submission
    if submit_type == "q":
        question = session.query(Question).filter_by(id=id).one()
        past_responses = get_question_responses(id, sunet)

        ok_to_grade = True
        # Check if the homework deadline has passed
        if question.hw.due_date and question.hw.due_date < datetime.utcnow():
            ok_to_grade = False
            question_response.score = 0
            question_response.comments = "You have passed the due date for "\
                "this homework. This submission has not been graded or saved."
            if past_responses:
                question_response.time = max(x.time for x in past_responses)
            else:
                question_response.time = ""

        # Check if they've submitted too much
        if ok_to_grade and len(past_responses) >= 2:
            last_response_time = max(x.time for x in past_responses)
            if datetime.utcnow() - last_response_time < timedelta(hours=6):
                ok_to_grade = False
                question_response.score = 0
                question_response.comments = "Please wait six hours since "\
                    "your last submission to submit again. This submission "\
                    "has not been graded or saved."
                question_response.time = last_response_time

        if ok_to_grade:
            items = session.query(Item).filter_by(question_id=id).all()

            score, comments = question.check(responses)

            question_response.score = score
            question_response.comments = comments
            for item, response in zip(items, responses):
                item_response = ItemResponse(item_id=item.id,
                                             response=response)
                question_response.item_responses.append(item_response)

            # add response to the database
            session.add(question_response)
            session.commit()

    # Sample question grading submission
    elif submit_type == "s":
        sample_responses = session.query(QuestionResponse).\
            filter_by(sunet="Sample Sam").\
            filter_by(question_id=id).all()

        assigned_scores = [float(resp) for resp in responses]
        true_scores = [float(resp.score) for resp in sample_responses]

        if assigned_scores == true_scores:
            session.query(GradingPermission).\
                filter_by(sunet=sunet).\
                filter_by(question_id=id).\
                update({"permissions": 1})
            session.commit()
            question_response.comments = "Congratulations! You are now "\
                "qualified to grade this question. Please refresh the "\
                "page to see the student responses."
        else:
            question_response.comments = "Sorry, but there is still a "\
                "discrepancy between your grades and the grades for this"\
                "sample response. Please try again."

    # Grading student questions
    elif submit_type == "g":
        # Make sure student was assigned this grading task
        task = session.query(GradingTask).get(id)
        if task.grader != sunet:
            abort(403)

        score = float(responses[0])
        comments = responses[1]

        question_grade = QuestionGrade(
            grading_task=task,
            time=datetime.utcnow(),
            score=score,
            comments=comments
        )
        session.add(question_grade)
        session.commit()

        question_response.comments = "Your scores have been "\
            "successfully recorded!"

    # Wrong submit_type
    else:
        abort(500)

    # add response to what to return to the user
    return json.dumps({"last_submission": question_response}, cls=NewEncoder)
