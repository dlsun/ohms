"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template, make_response, redirect
import json
from utils import NewEncoder, convert_to_last_name
from datetime import datetime
import xml.etree.ElementTree as ET
from collections import defaultdict

from objects import session, Homework, Question, PeerReview, User, GradingTask
from queries import get_user, get_homework, get_question, \
    get_question_response, get_last_question_response, \
    get_all_regular_questions, \
    get_all_responses_to_question, get_all_peer_tasks, \
    get_peer_review_questions, get_peer_tasks_for_student, \
    get_grading_task, add_grade, get_grade
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

@app.route("/materials")
def materials():
    user = validate_user()
    import os
    files = [f for f in os.listdir("%s/WWW/restricted/" % options.base_dir) if not f.startswith('.')]
    files.sort()
    return render_template("materials.html", user=user, files=files, options=options)

@app.route("/list")
def list():
    user = validate_user()
    hws = get_homework()
    
    # keep track of to-do list for peer reviews
    to_do = defaultdict(int)
    # keep track of the peer review corresponding to each question
    prq_map = {}
    for prq in get_peer_review_questions():
        prq.set_metadata()
        prq_map[prq.question_id] = prq

    for hw in hws:

        # skip if homework not due yet
        if hw.due_date > pdt_now():
            continue

        # iterate over questions
        for q in hw.questions:

            # check if q is a question that is peer-reviewed
            if q.id in prq_map:

                # if grading tasks haven't been assigned
                if not get_all_peer_tasks(q.id):
                
                    # get corresponding Peer Review object, instantiate with data from XML
                    prq = prq_map[q.id]

                    # get list of all students who responded, then shuffle
                    responders = [r.stuid for r in get_all_responses_to_question(q.id)]
                    import random
                    random.seed(q.id)
                    random.shuffle(responders)

                    # import engine
                    from base import engine

                    # assign peer grading tasks, if applicable
                    # (self grading tasks are assigned individually, on the fly)
                    tasks = []
                    m, n = len(prq.peer_pts), len(responders)
                    for i, stuid in enumerate(responders):
                        for offset in [k*(k+1)/2 for k in range(1, m+1)]:
                            j = (i + offset) % n
                            tasks.append({"grader": stuid, "student": responders[j], "question_id": q.id})
                    engine.execute(GradingTask.__table__.insert(), tasks)

            # if question itself is a peer review question
            elif isinstance(q, PeerReview):
                # compute updated score for student
                response = get_last_question_response(q.question_id, user.stuid)
                if response:
                    tasks = get_peer_tasks_for_student(q.question_id, user.stuid)
                    scores = [t.score for t in tasks if t.score is not None]
                    new_score = sorted(scores)[len(scores) // 2] if scores else None
                    if response.score is None:
                        response.score = new_score
                        response.comments = "Click <a href='rate?id=%d' target='_blank'>here</a> to view comments." % q.question_id
                        session.commit()
                    # check that student has rated all the peer reviews
                    for task in tasks:
                        if task.score is not None and task.rating is None:
                            to_do[response.question.homework] += 1

        # update student's grade on the homework
        calculate_grade(user, hw)


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
    question_list = get_all_regular_questions() if user.type == "admin" else None
    if user.type != "admin" and hw.start_date and hw.start_date > pdt_now():
        raise Exception("This homework has not yet been released.")
    else:
        return render_template("hw.html",
                               homework=hw,
                               user=user,
                               question_list=question_list,
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
    return json.dumps(question.load_response(user), cls=NewEncoder)


@app.route("/submit", methods=['POST'])
def submit():
    user = validate_user()
    q_id = request.args.get("q_id")
    question = get_question(q_id)
    responses = request.form.getlist('responses')
    out = question.submit_response(user.stuid, responses)
    return json.dumps(out, cls=NewEncoder)


def calculate_grade(user, hw):
    """
    helper function that calculates a student's grade on a given homework
    """

    # total up the points
    score = 0.
    if len(hw.questions) == 0:
        return None
    for q in hw.questions:
        out = q.load_response(user)
        if out['submission'] is None:
            continue
        elif out['submission'].score is None:
            return None
        else:
            score += out['submission'].score
    # fill in grades
    grade = get_grade(user.stuid, hw.id)
    if not grade:
        add_grade(user, hw, score)
    else:
        grade.score = score
    session.commit()

    return grade


@app.route("/grades")
def grades():
    user = validate_user()

    homeworks = get_homework()
    grades = {hw.id: get_grade(user.stuid, hw.id) for hw in homeworks}
    
    # fetch grades from gradebook
    return render_template("grades.html", homeworks=homeworks, 
                           grades=grades, options=options, user=user)


@app.route("/upload", methods=['POST'])
def upload():
    user = validate_user()

    file = request.files['file']
    if not file:
        return "No file uploaded."

    # extract the extension
    ext = file.filename.rsplit('.', 1)[1]

    # generate a random filename
    from string import ascii_lowercase, digits
    from random import choice
    filename = "".join(choice(ascii_lowercase + digits) for _ in range(40))
    filename += "." + ext

    # determine where to save the file
    path = "%s/WWW/%s/%s" % (options.base_dir, options.upload_dir, filename)
    file.save(path)

    # return the URL to the file
    url = "%s/%s/%s" % (options.base_url, options.upload_dir, filename)
    return '''
<script>
  var input1 = top.$('.mce-btn.mce-open').parent().find('.mce-textbox').val('%s');
  input1.parents(".mce-formitem").next().find(".mce-textbox").val('%s');
</script>''' % (url, url)


# ADMIN FUNCTIONS
@app.route("/admin")
def admin():
    admin = validate_admin()

    homeworks = get_homework()

    guests = session.query(User).filter_by(type="guest").all()
    admins = session.query(User).filter_by(type="admin").all()

    return render_template("admin/index.html", homeworks=homeworks, 
                           guests=guests, admins=admins,  
                           gradebook=get_gradebook(homeworks), options=options)

@app.route("/download_grades", methods=['GET'])
def download_grades():
    admin = validate_admin()

    homeworks = get_homework()
    gradebook = get_gradebook(homeworks)

    csv = '"Student",' + ','.join(('"' + hw.name.replace('"', '""') + '"') for hw in homeworks) + "\n"

    for student, grades in gradebook:
        row = [student.name]
        for hw in homeworks:
            if grades[hw.id] is None:
                row.append("")
            else:
                row.append(str(grades[hw.id].score))
        csv += ",".join(row) + "\n"

    response = make_response(csv)
    course = options.title.replace(" ", "")
    date = datetime.now().strftime("%m-%d-%Y")
    filename = "%sGrades%s.csv" % (course, date)
    response.headers["Content-Disposition"] = "attachment; filename=%s" % filename

    return response

def get_gradebook(homeworks):
    students = session.query(User).filter_by(type="student").all()
    students.sort(key=lambda user: convert_to_last_name(user.name))

    return [(s, {hw.id: get_grade(s.stuid, hw.id) for hw in homeworks}) for s in students]

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

    if not session.query(User).get(student):
        raise Exception("No user exists with the given ID.")

    session.query(User).filter_by(stuid=admin.stuid).update({
        "proxy": student
    })
    session.commit()

    return '''If you return to the main page now, you will be viewing the system 
from the perspective of user <b>%s</b>. To return to your own view, you must visit 
<a href="admin">/cgi-bin/index.cgi/admin</a> and enter your own ID.''' % admin.proxy

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

@app.route("/update_grade", methods=['POST'])
def update_grade():
    admin = validate_admin()

    stuid = request.form['stuid']
    hw_id = request.form['hw_id']
    score = request.form['score']
    score = None if score == "" else float(score)

    # fill in grades
    grade = get_grade(stuid, hw_id)
    if not grade:
        add_grade(get_user(stuid), get_homework(hw_id), score)
    else:
        grade.score = score
    session.commit()

    return "Grade update successful!"
