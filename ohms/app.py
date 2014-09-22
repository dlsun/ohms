"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template, make_response, redirect
import json
from utils import NewEncoder, convert_to_last_name
from datetime import datetime
import xml.etree.ElementTree as ET
from collections import defaultdict

from objects import session, Homework, Question, User, GradingTask
from queries import get_user, get_homework, get_question, \
    get_question_response, get_last_question_response, \
    get_all_responses_to_question, get_all_peer_tasks_for_question, \
    get_peer_review_questions, get_peer_tasks_for_student, \
    get_peer_tasks_for_grader, get_self_tasks_for_student, \
    get_grading_task, add_grade, get_all_grades, get_grade
import options
from pdt import pdt_now
from auth import validate_user, validate_admin

# Configuration based on deploy target
if options.target == "local":
    app = Flask(__name__, static_url_path="/static", static_folder="../static")
else:
    app = Flask(__name__)
    app.debug = (options.target != "prod")

    @app.errorhandler(Exception)
    def handle_exceptions(error):
        return make_response(error.message, 403)

@app.route("/")
def index():
    return render_template("index.html", options=options)

@app.route("/list")
def list():
    user = validate_user()
    hws = get_homework()
    
    to_do = defaultdict(int) # to-do list for peer reviews

    # iterate over the questions that are peer review questions
    peer_review_questions = get_peer_review_questions()
    for prq in peer_review_questions:

        # instantiate the object with data from the XML
        prq.set_metadata()

        # get student's response to the original question, if any
        response = get_last_question_response(prq.question_id, user.stuid)

        # if student answered the question
        if response:

            # check if the homework deadline has passed
            if response.question.homework.due_date < pdt_now():
                q_id = response.question_id
                # if student is required to do self assessment:
                if prq.self_pts is not None:
                    # and he/she hasn't been assigned the task yet, do it
                    if not get_self_tasks_for_student(q_id, user.stuid):
                        gt = GradingTask(grader=user.stuid,
                                         student=user.stuid,
                                         question_id=q_id)
                        session.add(gt)
                        session.commit()
                # check if student has already been assigned peer tasks
                tasks = get_peer_tasks_for_grader(q_id, user.stuid)
                n, m = len(tasks), len(prq.peer_pts)
                # if not, assign the tasks
                if n < m:
                    responses = get_all_responses_to_question(q_id)
                    tasks = get_all_peer_tasks_for_question(q_id)
                    pool = []
                    for r in responses:
                        if r.stuid == user.stuid:
                            continue
                        i = len([t for t in tasks if t.student == r.stuid])
                        pool.extend([r.stuid]*(m-i))
                    while n < m:
                        import random
                        student = random.choice(pool)
                        gt = GradingTask(grader=user.stuid,
                                         student=student,
                                         question_id=q_id)
                        session.add(gt)
                        pool = [p for p in pool if p != student]
                        n += 1
                    session.commit()

            # check if peer grading deadling has passed
            if prq.homework.due_date < pdt_now():
                # compute updated score for student
                tasks = get_peer_tasks_for_student(prq.question_id, user.stuid)
                scores = [t.score for t in tasks if t.score is not None]
                new_score = sorted(scores)[len(scores) // 2] if scores else None
                if response.score != new_score:
                    response.score = new_score
                    response.comments = "Click <a href='rate?id=%d' target='_blank'>here</a> to view comments." % prq.question_id
                    session.commit()
                # check that student has rated all the peer reviews
                for task in tasks:
                    if task.score is not None and task.rating is None:
                        to_do[response.question.homework] += 1

    return render_template("list.html", homeworks=hws,
                           user=user,
                           options=options,
                           current_time=pdt_now(),
                           to_do=to_do)


@app.route("/hw", methods=['GET'])
def hw():
    user = validate_user()
    hw_id = request.args.get("id")
    hw = get_homework(hw_id)
    if user.type != "admin" and hw.start_date and hw.start_date > pdt_now():
        raise Exception("This homework has not yet been released.")
    else:
        return render_template("hw.html",
                               homework=hw,
                               user=user,
                               options=options)


@app.route("/rate", methods=['GET'])
def rate():
    user = validate_user()
    question_id = request.args.get("id")
    tasks = get_peer_tasks_for_student(question_id, user.stuid)
    tasks = [t for t in tasks if t.score is not None]
    return render_template("rate.html",
                           grading_tasks=tasks,
                           options=options)

@app.route("/rate_submit", methods=['POST'])
def rate_submit():
    user = validate_user()
    task = get_grading_task(request.form.get('task_id'))
    task.rating = int(request.form.get('rating'))
    session.commit()
    return ""


@app.route("/load", methods=['GET'])
def load():
    user = validate_user()
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    return json.dumps(question.load_response(user.stuid), cls=NewEncoder)


@app.route("/submit", methods=['POST'])
def submit():
    user = validate_user()
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    responses = request.form.getlist('responses')
    out = question.submit_response(user.stuid, responses)
    calculate_grade(user, question.homework)
    return json.dumps(out, cls=NewEncoder)


def calculate_grade(user, hw):
    """
    helper function that calculates a student's grade on a given homework
    """

    # total up the points
    score, points = 0, 0
    for q in hw.questions:
        points += q.points
        out = q.load_response(user.stuid)
        if out['submission']:
            score += (out['submission'].score or 0.)
    # fill in grades
    grade = get_grade(user.stuid, hw.name)
    if not grade:
        add_grade(user.stuid, hw.name, hw.due_date, score, points)
    else:
        grade.time = hw.due_date
        grade.score = score
        grade.points = points
    session.commit()

    return grade


@app.route("/grades")
def grades():
    user = validate_user()
    grades = get_all_grades(user.stuid)
    
    # fetch grades from gradebook
    return render_template("grades.html", grades=grades, 
                           options=options, user=user)

# ADMIN FUNCTIONS
@app.route("/admin")
def admin():
    admin = validate_admin()

    homeworks = [hw for hw in get_homework() if hw.due_date <= pdt_now()]
    students = session.query(User).filter_by(type="student").all()
    students.sort(key=lambda user: convert_to_last_name(user.name))

    gradebook = []
    for student in students:
        gradebook.append((student, get_all_grades(student.stuid)))

    assignments = [g.assignment for g in gradebook[0][1]] if gradebook else []

    guests = session.query(User).filter_by(type="guest").all()
    admins = session.query(User).filter_by(type="admin").all()

    return render_template("admin/index.html", students=students, guests=guests, admins=admins,  
                           assignments=assignments, gradebook=gradebook, options=options)

@app.route("/change_user_type", methods=['POST'])
def change_user_type():
    admin = validate_admin()

    stuid = request.form['user']
    user_type = request.form['type']

    session.query(User).filter_by(stuid=stuid).update({
        "type": user_type
    })
    session.commit()

    return "Successfully changed user %s to %s." % (stuid, user_type)

@app.route("/update_question", methods=['POST'])
def update_question():
    admin = validate_admin()
    
    q_id = request.form['q_id']
    xml_new = request.form['xml']
    node = ET.fromstring(xml_new)
    node.attrib['id'] = q_id
    question = Question.from_xml(node)
    return json.dumps({
        "xml": question.xml,
        "html": question.to_html(),
    })
        
@app.route("/update_response", methods=['POST'])
def update_response():
    admin = validate_admin()

    response_id = request.form["response_id"]
    response = get_question_response(response_id)
    score = request.form["score"]
    response.score = float(score) if score else None
    response.comments = request.form["comments"]    
    session.commit()

    calculate_grade(response.user, response.question.homework)

    return "Updated score for student %s to %f." % (response.stuid, response.score)
    
@app.route("/view_responses")
def view_responses():
    admin = validate_admin()

    q_id = request.args.get('q')
    responses = get_all_responses_to_question(q_id)

    return render_template("admin/view_responses.html", responses=responses, options=options)

@app.route("/change_user", methods=['POST'])
def change_user():
    admin = validate_admin()
    student = request.form['user']

    try:
        session.query(User).get(student)
    except:
        raise Exception("No user exists with the given ID.")

    session.query(User).filter_by(stuid=admin.stuid).update({
        "proxy": student
    })
    session.commit()

    return "Successfully changed user to %s" % admin.proxy

@app.route("/add_homework", methods=['POST'])
def add_homework():
    admin = validate_admin()

    name = request.form['name']
    start_date = datetime.strptime(request.form['start_date'],
                                   "%m/%d/%Y %H:%M:%S")
    due_date = datetime.strptime(request.form['due_date'],
                                 "%m/%d/%Y %H:%M:%S")

    homework = Homework(name=name,
                        start_date=start_date,
                        due_date=due_date)
    session.add(homework)
    session.commit()

    return "%s added successfully!" % name

@app.route("/update_due_date", methods=['POST'])
def update_due_date():
    admin = validate_admin()

    hw_id = request.form['hw_id']
    start_date = datetime.strptime(request.form['start_date'],
                                   "%m/%d/%Y %H:%M:%S")
    due_date = datetime.strptime(request.form['due_date'],
                                 "%m/%d/%Y %H:%M:%S")
    homework = get_homework(hw_id)
    homework.start_date = start_date
    homework.due_date = due_date
    session.commit()

    return "Due date for %s updated successfully!" % homework.name


@app.route("/add_question", methods=['POST'])
def add_question():
    admin = validate_admin()

    xml = request.form['xml']
    node = ET.fromstring(xml)

    # remove any ID tags
    for e in node.iter():
        if "id" in e.attrib: e.attrib.pop("id")

    question = Question.from_xml(node)
    question.homework = get_homework(request.form['hw_id'])

    session.commit()

    return "Question added successfully!"

