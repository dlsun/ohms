"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime, timedelta

from base import session
from objects import Question, QuestionResponse, ItemResponse, User
from queries import get_user, get_homework, get_question, \
    get_question_response, get_last_question_response, \
    set_grading_permissions, get_peer_review_questions, \
    get_grading_tasks_for_grader, get_grading_tasks_for_student, \
    get_sample_responses
import options
from collections import defaultdict


# Configuration based on deploy target
if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
    sunet = "test"
    user = User(sunet=sunet,
                name="Test User",
                type="admin",
                group=0)
else:
    app = Flask(__name__)
    app.debug = (options.target != "prod")

    @app.errorhandler(Exception)
    def handle_exceptions(error):
        return make_response(error.message, 403)

    ### THIS IS STUFF THAT SHOULD BE FACTORED OUT
    sunet = os.environ.get("WEBAUTH_USER")
    if not sunet:
        raise Exception("You are no longer logged in. Please refresh the page.")
    try:
        user = get_user(sunet)
    except:
        user = User(sunet=sunet,
                    name=os.environ.get("WEBAUTH_LDAP_DISPLAYNAME"),
                    type="student")
        session.add(user)
        session.commit()


@app.route("/")
def index():
    hws = get_homework()
    
    # a to-do list
    to_do = defaultdict(int)

    # get all peer review items
    peer_review_questions = get_peer_review_questions()
    for prq in peer_review_questions:

        response = get_last_question_response(prq.question_id, user.sunet)
        # if deadline has passed...
        if prq.homework.due_date < datetime.now():
            tasks = get_grading_tasks_for_student(prq.question_id, user.sunet)
            # if student doesn't have score, tabulate scores from peer reviews
            if response.score is None:
                scores = [t.score for t in tasks if t is not None]
                if scores:
                    response.score = sorted(scores)[len(scores) // 2]
                    session.commit()
            # check that student has rated all the peer reviews
            for task in tasks:
                if task.score is not None and task.rating is None:
                    to_do[response.question.homework.name] += 1

    return render_template("index.html", homeworks=hws,
                           peer_grading=peer_grading,
                           user=user,
                           options=options,
                           current_time=datetime.now(),
                           to_do=to_do
    )


@app.route("/hw", methods=['GET'])
def hw():
    hw_id = request.args.get("id")
    homework = get_homework(hw_id)
    if user.type != "admin" and homework.start_date and homework.start_date > datetime.now():
        raise Exception("This homework has not yet been released.")
    else:
        return render_template("hw.html",
                               homework=homework,
                               user=user,
                               options=options)


@app.route("/rate", methods=['GET'])
def rate():

    out = {}
    question_response_id = request.args.get("id")

    # check that student is the one who submitted this QuestionResponse
    question_response = get_question_response(question_response_id)
    if question_response.sunet != sunet and user.type != "admin":
        raise Exception("You are not authorized to rate this response.")

    # fetch all peers that were assigned to grade this QuestionResponse
    grading_tasks = get_grading_tasks_for_response(question_response_id)

    return render_template("rate.html", 
                           grading_tasks=grading_tasks,
                           options=options)


@app.route("/load", methods=['GET'])
def load():

    out = {}
    q_id = request.args.get("q_id")

    # if loading a student response to a question
    if q_id[0] == "q":
        question_id = q_id[1:]
        question = get_question(question_id)
        out = question.load_response(sunet)

    # if loading a student's scores for a sample response (not currently functional)
    elif q_id[0] == "s":
        question_id = q_id[1:]
        question = get_question(question_id)
        out['locked'] = (datetime.now() > question.homework.due_date)

    # if loading a student rating to a peer grade
    elif q_id[0] == "r":
        grading_task_id = q_id[1:]
        grading_task = get_grading_task(grading_task_id)
        if grading_task.rating:
            out['submission'] = {
                "item_responses": [ {"response": grading_task.rating} ]
                }
        out['locked'] = False

    return json.dumps(out, cls=NewEncoder)


@app.route("/submit", methods=['POST'])
def submit():
    q_id = request.args.get("q_id")
    submit_type = q_id[0]
    id = q_id[1:]

    responses = request.form.getlist('responses')

    if submit_type == "q":
        question = get_question(q_id[1:])
        out = question.submit_response(sunet, responses)

    # Sample question grading submission
    elif submit_type == "s":

        question_response = QuestionResponse(
        sunet=sunet,
        time=datetime.now(),
        question_id=id
        )

        is_locked = False

        sample_responses = get_sample_responses(id)

        assigned_scores = [float(resp) for resp in responses]
        true_scores = [float(resp.score) for resp in sample_responses]

        if assigned_scores == true_scores:
            set_grading_permissions(id, sunet, 1)
            summary_comment = '''
<p>Congratulations! You are now
qualified to grade this question. Please refresh the 
page to see the student responses.</p>'''
        else:
            summary_comment = '''
<p>Sorry, but there's a discrepancy between your score and the 
instructor scores for these sample responses. Please try again.</p>'''

        summary_comment += '''
<p>Instructor comments for each response should now appear 
above. They are intended to help you determine why each response earned 
the score it did.</p>'''

        question_response.comments = [r.comments for r in sample_responses]
        question_response.comments.append(summary_comment)

        out = json.dumps({
            "locked": is_locked,
            "submission": question_response
            })

    # Rating the peer reviews
    elif submit_type == "r":
        is_locked = False

        # Make sure student was assigned to rate this
        rating = request.form.getlist('responses')[0]
        grading_task = get_grading_task(id)
        if grading_task.student == sunet:
            grading_task.rating = rating
            session.commit()
        else:
            raise Exception("You are not authorized to rate this comment.")

        # Make question_response object to return
        question_response = QuestionResponse(
            sunet=sunet,
            time=datetime.now(),
            question_id=id,
            comments="Rating submitted successfully!"
            )

        out = json.dumps({
            "locked": is_locked,
            "submission": question_response
            })
        
    # Wrong submit_type
    else:
        raise Exception("Invalid submission.")

    # Add response to what to return to the user
    return json.dumps(out, cls=NewEncoder)


# For local development--this does not run in prod or test
if __name__ == "__main__":
    app.run(debug=True)
