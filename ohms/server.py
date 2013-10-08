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
from queries import get_question_responses, get_question_grades, get_grading_permissions, get_user
import options


# Configuration based on deploy target
if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
else:
    app = Flask(__name__)

app.debug = (options.target != "prod")

if options.target != "local":
    sunet = os.environ.get("WEBAUTH_USER")
    try:
        user = get_user(sunet)
    except:
        user = User(sunet=sunet,
                    name=os.environ.get("WEBAUTH_LDAP_DISPLAYNAME"),
                    type="student")
        session.add(user)
        session.commit()
else:
    sunet = "parkerp1"
    user = User(sunet=sunet,
                name="Guest User",
                type="student")

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
        return json.JSONEncoder.default(self, obj)


@app.route("/")
def index():
    hws = session.query(Homework).all()
    
    # get list of whether user was assigned to peer grading or not
    from treatment_assignments import treatments, group_assignments
    if sunet in group_assignments:
        group = group_assignments[sunet]
        peer_grading = treatments[group]
    elif user.type == "admin" or user.type == "grader":
        peer_grading = [1,1,1,1,1,1,1,1,1]
    else:
        peer_grading = [-1,-1,-1,-1,-1,-1,-1,-1,-1]

    return render_template("index.html", homeworks=hws,
                           peer_grading=peer_grading,
                           user=user,
                           options=options)


@app.route("/hw", methods=['GET'])
def hw():
    hw_id = request.args.get("id")
    homework = session.query(Homework).filter_by(id=hw_id).one()
    return render_template("hw.html",
                           homework=homework,
                           user=user,
                           options=options)


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

    return render_template("grade.html",
                           questions=questions,
                           user=user,
                           options=options)


@app.route("/rate", methods=['GET'])
def rate():

    out = {}
    question_response_id = request.args.get("id")

    # check that student is the one who submitted this QuestionResponse
    question_response = session.query(QuestionResponse).get(question_response_id)
    if question_response.sunet != sunet:
        abort(403)

    # fetch all peers that were assigned to grade this QuestionResponse
    grading_tasks = session.query(GradingTask).\
        filter_by(question_response_id=question_response_id).all()
    question_grades = []
    for task in grading_tasks:
        submissions = session.query(QuestionGrade).\
            filter_by(grading_task_id=task.id).\
            order_by(QuestionGrade.time).all()
        if submissions:
            question_grades.append(submissions[-1])

    return render_template("rate.html", 
                           question_grades=question_grades,
                           options=options)


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

    # if loading a student response to a question
    if q_id[0] == "q":
        question_id = q_id[1:]
        question = session.query(Question).get(question_id)
        submissions = get_question_responses(question_id, sunet)
        out['submission'] = submissions[-1] if submissions else None
        out['locked'] = check_if_locked(question.hw.due_date, submissions)
        if datetime.now() > question.hw.due_date:
            out['solution'] = [item.solution for item in question.items]

    # if loading a student's peer grade for an actual student's response
    elif q_id[0] == "g":
        grading_task_id = q_id[1:]
        question_id = session.query(GradingTask).get(grading_task_id).question_response.question_id
        question_grades = get_question_grades(grading_task_id, sunet)
        if question_grades:
            out['submission'] = {
                "time": datetime.now(),
                "item_responses": [
                    {"response": question_grades[-1].score},
                    {"response": question_grades[-1].comments}
                    ]
                }
        permission = get_grading_permissions(question_id, sunet)
        out['locked'] = (datetime.now() > permission.due_date)

    # if loading a student's scores for a sample response (not currently functional)
    elif q_id[0] == "s":
        question_id = q_id[1:]
        permission = get_grading_permissions(question_id, sunet)
        out['locked'] = (datetime.now() > permission.due_date)

    # if loading a student rating to a peer grade
    elif q_id[0] == "r":
        question_grade_id = q_id[1:]
        question_grade = session.query(QuestionGrade).get(question_grade_id)
        if question_grade.rating:
            out['submission'] = {
                "item_responses": [ {"response": question_grade.rating} ]
                }
        out['locked'] = False

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

    # Rating the peer reviews
    elif submit_type == "r":
        is_locked = False

        # Make sure student was assigned to rate this
        rating = request.form.getlist('responses')[0]
        entry = session.query(QuestionGrade).filter_by(id=id)
        if entry.one().grading_task.question_response.sunet == sunet:
            entry.update({"rating": rating})
        else:
            abort(403)
        session.commit()

        question_response.comments = "Rating submitted successfully!"
        

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
