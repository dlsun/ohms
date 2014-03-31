"""
OHMS: Online Homework Management System
"""

import os
from flask import Flask, request, render_template, make_response
import json
from utils import NewEncoder
from datetime import datetime
import random

from base import session
from objects import User, Homework, Question, QuestionResponse, GradingTask, LongAnswerItem
from queries import get_user
from send_email import send_all
import options
from auth import auth_stuid, auth_student_name

import smtplib

if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
    stuid = "test"
    user = User(stuid=stuid,
                name="Test User",
                type="admin",
                group=0)
else:
    app = Flask(__name__)
    app.debug = (options.target != "prod")

    @app.errorhandler(Exception)
    def handle_exceptions(error):
        return make_response(error.message, 403)

    stuid = auth_stuid()
    if not stuid:
        raise Exception("You are no longer logged in. Please refresh the page.")
    try:
        user = get_user(stuid)
    except:
        user = User(stuid=stuid,
                    name=auth_student_name(),
                    type="student")
        session.add(user)
        session.commit()

@app.route("/")
def index():
    return render_template("admin/index.html", options=options, user=user)


@app.route("/assign_tasks/<int:hw_id>", methods=['POST'])
def assign_tasks(hw_id):

    homework = session.query(Homework).get(hw_id)
    groups = request.form.getlist('group')
    
    users = session.query(User).filter(User.group.in_(groups)).all()
    due_date = datetime.strptime(request.form["due_date"],
                                 "%Y-%m-%d %H:%M:%S")

    # store the users who were not assigned because they didn't complete HW
    not_assigned = set()

    for q in homework.questions:

        # only if this is a peer graded question
        if not isinstance(q.items[0], LongAnswerItem):
            continue

        # get responses from only the relevant users
        responses = []
        for user in users:
            submit = get_last_question_response(q.id, user.stuid)
            if submit:
                responses.append(submit)
            else:
                not_assigned.add(user)

        # shuffle the responses and iterate over them
        n = len(responses)
        random.seed(q.id) # setting a seed will be useful for debugging
        random.shuffle(responses)
        for i, r in enumerate(responses):
            # update comments section with link to peer comments
            r.comments = "Click <a href='rate?id=%d' target='_blank'>here</a> to view and respond to feedback from your peers." % r.id
            
            # assign user permissions for this question
            gp = GradingPermission(stuid=r.stuid, question_id=q.id,
                                   permissions=1, due_date=due_date)
            session.add(gp)
            
            # assign this user other responses to grade
            for offset in [1, 3, 6]:
                j = (i + offset) % n
                gt = GradingTask(grader=r.stuid, question_response=responses[j])
                session.add(gt)

    session.commit()

    # Send email notifications to studnts who were assigned to all questions
    assigned_users = [u for u in users if u not in not_assigned]
    send_all(assigned_users, "Peer Assessment for %s is Ready" % homework.name,
r"""Dear %s,

You've been assigned to assess your peers this week. The assessments are 
due {due_date}. 

You will be able to view your peer's comments on your answers as they 
are submitted, but your score will not be available until {due_date}. 
At that time, please log in to view and respond to the comments you 
received from your peers.

Best,
STATS 60 Staff""".format(due_date=due_date.strftime("%A, %b %d at %I:%M %p")))

    # Send slightly different email to students who were not assigned to all questions
    send_all(not_assigned, "Peer Assessment for %s is Ready" % homework.name,
r"""Dear %s,

You've been assigned to assess your peers this week. The assessments are 
due {due_date}. 

Our records indicate that you did not complete all of the free response  
questions this week. Please note that you are allowed to evaluate others' 
responses only if you attempted that question yourself. Therefore, you 
may not have been assigned any evaulation tasks for some or all of the 
questions. In the future, please be sure to finish the homework on time 
in order to participate in peer assessment.

You will be able to view your peer's comments on your answers as they 
are submitted, but your score will not be available until {due_date}. 
At that time, please log in to view and respond to the comments you 
received from your peers.

Best,
STATS 60 Staff""".format(due_date=due_date.strftime("%A, %b %d at %I:%M %p")))

    # Send email to the course staff
    admins = session.query(User).filter_by(type="admin").all()
    send_all(admins, "Peer Assessment for %s is Ready" % homework.name,
r"""Dear %s (and other members of the STATS 60 Staff),

Just letting you know that the peer assessment for this week was just released. 
It is due at {due_date}.

If you were assigned to grade for this week, please do so between now and 
{due_date}.

Sincerely,
OHMS

P.S. This is an automatically generated message ;-)
""".format(due_date=due_date.strftime("%A, %b %d at %I:%M %p")))

    return r'''Successfully assigned %d students. You should have received an 
e-mail confirmation.''' % len(responses)


@app.route("/reminder_email/<int:hw_id>", methods=['POST'])
def reminder_email(hw_id):

    homework = session.query(Homework).get(hw_id)

    # get users who haven't completed peer grading
    users = set()
    for question in homework.questions:
        tasks = session.query(GradingTask).join(QuestionResponse).\
                filter(QuestionResponse.question_id == question.id).all()
        for task in tasks:
            grades = session.query(QuestionGrade).filter_by(grading_task_id=task.id).all()
            if not grades:
                users.add(task.grader)

    # send e-mails
    users = [session.query(User).get(u) for u in users]
    message = '''Dear %s,\n\n''' + request.form['message'].replace("%", "%%") + '''

Best,
Stats 60 Staff
'''
    send_all(users, request.form['subject'], message)
    
    admins = session.query(User).filter_by(type="admin").all()
    send_all(admins, "%s Peer Assessment Reminder Sent" % homework.name,
"""Hey %s (and other staff),

A reminder e-mail was just sent to the following users to remind them to complete their 
peer assessments.\n\n""" + "\n".join(u.stuid for u in users) + """

Sincerely,
OHMS

P.S. This is an automatically generated message ;-)""")

    return "Sent reminder to %d recipients. You should have received an e-mail." % len(users)
    
@app.errorhandler(Exception)
def handle_exceptions(error):
    return make_response(error.message, 403)
