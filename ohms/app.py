"""
OHMS: Online Homework Management System
"""

from flask import Flask, request, render_template, make_response, redirect, url_for
import json
from utils import NewEncoder, convert_to_last_name
from datetime import datetime
import xml.etree.ElementTree as ET
from collections import defaultdict

from objects import session, Homework, Question, PeerReview, User, GradingTask, Grade, Category
from queries import get_user, get_homework, get_homeworks_before, get_question, \
    get_question_response, get_last_question_response, \
    get_all_regular_questions, \
    get_all_responses_to_question, get_all_peer_tasks, \
    get_peer_review_questions, get_peer_tasks_for_student, \
    get_grading_task, add_grade, get_grade, get_users
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

@app.route("/refresh_grades")
def refresh_grades():
    """
    This updates all students' grades on all homeworks.
    """
    homeworks = get_homework()
    students = get_students()
    for student in students:
        update_hw_grades(student, homeworks)
        print student.name
    session.commit()
    return "Successfully updated all students' grades."


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
def hw_list():
    user = validate_user()
    homeworks = get_homework()
    categories = session.query(Category).all()

    to_do = update_hw_grades(user, homeworks)
    session.commit()

    return render_template("list.html", homeworks=homeworks, categories=categories,
                           user=user,
                           options=options,
                           current_time=pdt_now(),
                           to_do=to_do)

def update_hw_grades(user, homeworks):
    """ 
    helper function that computes user's grades on homeworks, 
    returns a list of uncompleted peer reviews
    """

    # keep track of to-do list for peer reviews
    to_do = defaultdict(int)
    # keep track of the peer review corresponding to each question
    prq_map = {}
    for prq in get_peer_review_questions():
        prq.set_metadata()
        prq_map[prq.question_id] = prq

    for hw in homeworks:

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
                    # check that student has rated all the peer reviews
                    for task in tasks:
                        if task.score is not None and task.rating is None:
                            to_do[response.question.homework] += 1

        # update student's grade on the homework
        calculate_grade(user, hw)

    return to_do


@app.route("/hw", methods=['GET'])
def hw():
    user = validate_user()
    hw_id = request.args.get("id")
    hw = get_homework(hw_id)
    question_list = get_all_regular_questions() if user.type == "admin" else None

    if user.type == "admin":
        return render_template("hw.html",
                               hw_list=get_homework(),
                               homework=hw,
                               user=user,
                               question_list=question_list,
                               options=options)
    else:
        if hw.start_date and hw.start_date > pdt_now():
            raise Exception("This homework has not yet been released.")
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
    elif grade.score != score:
        grade.score = score
    else:
        return grade

    return grade


@app.route("/grades")
def grades():
    user = validate_user()

    categories = session.query(Category).all()
    homeworks = get_homeworks_before()

    update_hw_grades(user, homeworks)
    session.commit()

    gradebook, max_scores = get_gradebook()

    grades = [entry for entry in gradebook if entry[0] == user]

    if grades:
        grades = grades[0][1]
    else:
        grades = {hw.id: get_grade(user.stuid, hw.id) for hw in homeworks}
    
    return render_template("grades.html", homeworks=homeworks, 
                           grades=grades, max_scores=max_scores,
                           options=options, user=user,
                           categories=categories)


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

    # change back to admin view
    admin.proxy = admin.stuid
    session.commit()

    homeworks = get_homework()
    categories = session.query(Category).all()

    users = get_users()
    guests = []
    admins = []
    for user in users:
        if user.type == "guest":
            guests.append(user)
        elif user.type == "admin":
            admins.append(user)

    gradebook, max_scores = get_gradebook()
    
    return render_template("admin/index.html", homeworks=homeworks, 
                           guests=guests, admins=admins, categories=categories,
                           gradebook=gradebook, max_scores=max_scores, options=options)

@app.route("/download_grades", methods=['GET'])
def download_grades():
    admin = validate_admin()

    homeworks = get_homework()
    categories = session.query(Category).all()
    gradebook, max_scores = get_gradebook()

    csv = '"SUNet","Student","Overall",'
    csv += ','.join(('"' + c.name.replace('"', '""') + ' Total"') for c in categories) + ","
    csv += ','.join(('"' + hw.name.replace('"', '""') + '"') for hw in homeworks) + "\n"

    csv += ',"MAXIMUM",,' + ",".join("" for c in categories) + "," 
    csv += ",".join(str(max_scores[hw.id]) for hw in homeworks) + "\n"
    
    for student, grades in gradebook:
        row = [student.stuid, student.name, str(grades["overall"])]
        for category in categories:
            row.append(str(grades[category.name]))
        for hw in homeworks:
            if hw.id not in grades:
                row.append("")
            else:
                row.append("E" if grades[hw.id].excused else str(grades[hw.id].score))
        csv += ",".join(row) + "\n"
        
    response = make_response(csv)
    course = options.title.replace(" ", "")
    date = datetime.now().strftime("%m-%d-%Y")
    filename = "%sGrades%s.csv" % (course, date)
    response.headers["Content-Disposition"] = "attachment; filename=%s" % filename

    return response

@app.route("/download_peer_reviews", methods=['GET'])
def download_peer_reviews():
    admin = validate_admin()

    tasks = session.query(GradingTask).all()
    csv = "grader,student,question,score,comments,rating\n"

    for t in tasks:
        row = []
        for item in [t.grader, t.student, t.question_id, t.score, t.comments, t.rating]:
            if item is not None:
                row.append('"' + str(item).replace('"', '""') + '"')
            else:
                row.append('""')
        csv += ",".join(row) + "\n"

    response = make_response(csv)
    course = options.title.replace(" ", "")
    filename = "%sPeerAssessments.csv" % course
    response.headers["Content-Disposition"] = "attachment; filename=%s" % filename

    return response

def get_gradebook():
    """
    helper function that gets the gradebook
    """

    user = validate_user()

    if user.type == "admin":
        homeworks = get_homework()
    else:
        homeworks = get_homeworks_before()

    # get all the grades, put them into a gradebook
    gradebook, max_scores = {}, {}

    for user in get_users():
        if user.type == "student":
            gradebook[user] = {}

    for homework in homeworks:
        
        grades = session.query(Grade).filter_by(hw_id = homework.id).all()

        scores = []
        for g in grades:
            if g.student not in gradebook:
                continue
            gradebook[g.student][homework.id] = g
            try:
                scores.append(float(g.score))
            except:
                pass

        if homework.max_score is not None:
            max_scores[homework.id] = homework.max_score
        elif scores:
            max_scores[homework.id] = max(scores)
        else:
            max_scores[homework.id] = None
            
    gradebook = gradebook.items()
    gradebook.sort(key=lambda entry: convert_to_last_name(entry[0].name))

    categories = session.query(Category).all()
    
    # calculate total scores by category, taking into account excused assignments
    for student, grades in gradebook:
        earned = {c: [] for c in categories}
        possible = {c: [] for c in categories}
        for hw in homeworks:
            if max_scores[hw.id] is None or max_scores[hw.id] == 0:
                continue
            possible[hw.category].append(max_scores[hw.id])
            if hw.id in grades:
                if grades[hw.id].excused: # if student was excused from assignment
                    possible[hw.category].remove(max_scores[hw.id]) # don't count it against
                else:
                    try:
                        earned[hw.category].append(float(grades[hw.id].score))
                    except:
                        earned[hw.category].append(0)
            else:
                earned[hw.category].append(0)

        # add grades to gradebook
        grades["overall"] = 0.
        for category, poss in possible.iteritems():
            if len(poss) == 0:
                grades[category.name] = "0 / 0"
                continue
            # sort scores by benefit to grade if dropped
            e, p = sum(earned[category]), sum(poss)
            if len(poss) > category.drops + 1:
                grades_sorted = sorted(zip(earned[category], poss), key=lambda x: -(e-x[0])/(p-x[1]))
                grades_sorted = grades_sorted[category.drops:]
                out = zip(*grades_sorted)
            else:
                out = earned[category], poss
            grades[category.name] = "%0.1f / %0.1f" % (sum(out[0]), sum(out[1]))
            if sum(out[1]) > 0:
                grades["overall"] += category.weight * sum(out[0]) / sum(out[1])
                
    return gradebook, max_scores

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

@app.route("/move_question", methods=['POST'])
def move_question():
    admin = validate_admin()

    q_id = int(request.form['q_id'])
    hw_id = int(request.form['hw_id'])

    question = get_question(q_id)
    question.hw_id = hw_id if hw_id else None
    session.commit()

    if hw_id:
        return "Question ID %d moved to <a href=hw?id=%d>%s</a>." % (q_id, question.homework.id, question.homework.name)
    else:
        return "Question ID %d has been deleted!" % q_id

    
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
    calculate_grade(response.user, response.question.homework)
    session.commit()

    return "Updated score for student %s to %f." % (response.stuid, response.score)
    
@app.route("/view_responses")
def view_responses():
    admin = validate_admin()

    q_id = request.args.get('q')
    responses = get_all_responses_to_question(q_id)

    return render_template("admin/view_responses.html", responses=responses, options=options)

@app.route("/change", methods=['GET'])
def change_user():
    admin = validate_admin()
    student = request.args['user']

    if not session.query(User).get(student):
        raise Exception("No user exists with the given ID.")

    admin.proxy = student
    session.commit()

    return redirect(url_for('hw_list'))

@app.route("/add_homework", methods=['POST'])
def add_homework():
    admin = validate_admin()

    name = request.form['name']
    start_date = datetime.strptime(request.form['start_date'],
                                   "%m/%d/%Y %H:%M:%S")
    due_date = datetime.strptime(request.form['due_date'],
                                 "%m/%d/%Y %H:%M:%S")
    category_id = request.form['category_id']

    homework = Homework(name=name,
                        start_date=start_date,
                        due_date=due_date,
                        category_id=category_id)
    session.add(homework)
    session.commit()

    return "%s added successfully!" % name

@app.route("/export_hw", methods=['GET'])
def export_homework():
    admin = validate_admin()

    hw_id = request.args['id']
    hw = get_homework(hw_id)
    
    xml = "\n\n".join(q.xml for q in hw.questions)
    return xml

@app.route("/update_hw_name", methods=['POST'])
def update_hw_name():
    admin = validate_admin()

    hw_id = request.form['hw_id']
    hw_name = request.form['hw_name']

    homework = get_homework(hw_id)
    homework.name = hw_name
    session.commit()

    return '''The homework name was successfully updated to "%s"!''' % homework.name


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
    score = request.form['score'].strip()
    excused = 1 if request.form['excused'] == "true" else 0

    # check that score is valid
    try:
        float(score)
    except:
        assert(score in ["", "E"])

    # fill in grades
    grade = get_grade(stuid, hw_id)
    if not grade:
        add_grade(get_user(stuid), get_homework(hw_id), score, excused)
    else:
        grade.score = score
        grade.excused = excused
    session.commit()

    return "Grade update successful!"

@app.route("/update_max_score", methods=['POST'])
def update_max_score():
    admin = validate_admin()

    hw_id = request.form['hw_id']
    max_score = request.form['max_score'].strip()

    homework = get_homework(hw_id)
    homework.max_score = None if max_score == "" else float(max_score)
    session.commit()

    return "The maximum score for %s has been successfully updated!" % homework.name

@app.route("/update_category", methods=['POST'])
def update_category():
    admin = validate_admin()

    name = request.form['name']
    weight = float(request.form['weight'])
    drops = int(request.form['drops'])

    try:
        category_id = int(request.form['id'])
        category = session.query(Category).get(category_id)
        category.name = name
        category.weight = weight
        category.drops = drops
    except:
        session.add(Category(name=name, weight=weight, drops=drops))

    session.commit()

    return "Category %s successfully added/updated." % name


