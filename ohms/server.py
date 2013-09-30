"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, abort
import json
from datetime import datetime, timedelta

from base import session
from objects import Homework, Question, Item, QuestionResponse, ItemResponse
from objects import GradingTask, QuestionGrade, GradingPermission, User
from queries import get_question_responses, get_question_grades, exists_user
import options


# Configuration based on deploy target
if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
else:
    app = Flask(__name__)

app.debug = (options.target != "prod")

if options.target != "local":
    sunet = os.environ.get("WEBAUTH_USER")
    if not exists_user(sunet):
        user = User(sunet=sunet,
                    name=os.environ.get("WEBAUTH_LDAP_DISPLAYNAME"),
                    type="student")
        session.add(user)
        session.commit()
else:
    sunet = "dlsun"


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
    permissions = session.query(GradingPermission).\
        filter_by(sunet=sunet).all()
    peer_grade = set(p.question.hw_id for p in permissions)
    return render_template("index.html", homeworks=hws,
                           peer_grade=peer_grade,
                           options=options)


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


def check_if_locked(due_date, submissions):
    past_due = due_date and due_date < datetime.now()
    if len(submissions) > 1:
        last_time = max(x.time for x in submissions)
        too_many_submissions = datetime.now() < last_time + timedelta(hours=6)
    else:
        too_many_submissions = False
    return past_due or too_many_submissions


@app.route("/load", methods=['GET'])
def load():

    out = {}
    q_id = request.args.get("q_id")
    id = q_id[1:]

    if q_id[0] == "q":
        question = session.query(Question).filter_by(id=id).one()
        submissions = get_question_responses(id, sunet)
        out['locked'] = check_if_locked(question.hw.due_date, submissions)
        if datetime.now() > question.hw.due_date:
            out['solution'] = [item.solution for item in question.items]

    elif q_id[0] == "g":
        submissions = get_question_grades(id, sunet)
        out['locked'] = False

    out['submission'] = submissions[-1] if submissions else None

    return json.dumps(out, cls=NewEncoder)


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    submit_type = q_id[0]
    id = q_id[1:]

    responses = request.form.getlist('responses')

    question_response = QuestionResponse(
        sunet=sunet,
        time=datetime.now(),
        question_id=id
    )

    # Question submission
    if submit_type == "q":
        question = session.query(Question).filter_by(id=id).one()
        submissions = get_question_responses(id, sunet)

        is_locked = check_if_locked(question.hw.due_date, submissions)

        if not is_locked:

            score, comments = question.check(responses)

            question_response.score = score
            question_response.comments = comments
            for item, response in zip(question.items, responses):
                item_response = ItemResponse(item_id=item.id,
                                             response=response)
                question_response.item_responses.append(item_response)

            # add response to the database
            session.add(question_response)
            session.commit()

            submissions.append(question_response)
            is_locked = check_if_locked(question.hw.due_date, submissions)

        else:
            abort(403)

    # Sample question grading submission
    elif submit_type == "s":
        is_locked = False

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
                "discrepancy between your grades and the grades for this "\
                "sample response. Please try again."

    # Grading student questions
    elif submit_type == "g":
        is_locked = False

        # Make sure student was assigned this grading task
        task = session.query(GradingTask).get(id)
        if task.grader != sunet:
            abort(403)

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

        question_response.comments = "Your scores have been "\
            "successfully recorded!"

    # Wrong submit_type
    else:
        abort(500)

    # add response to what to return to the user
    return json.dumps({
        "locked": is_locked,
        "submission": question_response,
    }, cls=NewEncoder)


@app.route("/staff")
def staff():
    return render_template("office_hours.html", options=options)


@app.route("/handouts")
def handouts():
    handouts = os.listdir("/afs/ir/class/stats60/WWW/handouts")
    return render_template("handouts.html", handouts=handouts, options=options)


# For local development--this does not run in prod or test
if __name__ == "__main__":
    app.run(debug=True)
