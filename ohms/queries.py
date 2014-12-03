"""
queries.py

Some useful sql queries.
"""

from base import session
from objects import QuestionResponse, GradingTask, User, \
    Homework, Question, PeerReview, Grade
from pdt import pdt_now


def get_last_due_homework():
    """Returns the last homework that was due"""
    now = pdt_now()
    hws = reversed(session.query(Homework).order_by(Homework.due_date).all())
    for hw in hws:
        if hw.due_date < now:
            return hw

def get_last_two_due_homeworks():
    now = pdt_now()
    hws = session.query(Homework).order_by(Homework.due_date).all()
    due_hws = [hw for hw in hws if hw.due_date < now]
    return due_hws[-2:]
 

def get_homework(hw_id=None):
    if hw_id is None:
        return session.query(Homework).order_by(Homework.due_date).all()
    else:
        return session.query(Homework).get(hw_id)

def get_question(question_id):
    return session.query(Question).get(question_id)

def get_all_regular_questions():
    return [q for q in session.query(Question).\
                filter(Question.hw_id != None).\
                all() if not isinstance(q, PeerReview)]

def get_peer_review_questions():
    return session.query(PeerReview).filter(PeerReview.hw_id != None).all()


def get_question_response(question_response_id):
    return session.query(QuestionResponse).get(question_response_id)

def get_question_responses(question_id, stuid):
    return session.query(QuestionResponse).\
        filter_by(stuid=stuid).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.time).all()

def get_last_question_response(question_id, stuid):
    qrs = get_question_responses(question_id, stuid)
    return qrs[-1] if qrs else None

def get_all_responses_to_question(question_id):
    users = session.query(User).filter_by(type="student").all()
    responses = []
    for u in users:
        response = get_last_question_response(question_id, u.stuid)
        if response:
            responses.append(response)
    return responses

def get_grading_task(grading_task_id):
    return session.query(GradingTask).get(grading_task_id)

def get_all_peer_tasks(question_id):
    return session.query(GradingTask).filter_by(question_id=question_id).\
        filter(GradingTask.grader != GradingTask.student).all()

def get_peer_tasks_for_grader(question_id, stuid):
    return session.query(GradingTask).\
        filter_by(grader=stuid).join(Question).\
        filter(Question.id == question_id).\
        filter(GradingTask.student != stuid).\
        order_by(GradingTask.id).all()

def get_self_tasks_for_student(question_id, stuid):
    return session.query(GradingTask).\
        filter_by(grader=stuid).join(Question).\
        filter(Question.id == question_id).\
        filter(GradingTask.student == stuid).\
        all()

def get_peer_tasks_for_student(question_id, stuid):
    return session.query(GradingTask).\
        filter_by(student=stuid).join(Question).\
        filter(Question.id == question_id).\
        filter(GradingTask.grader != stuid).\
        order_by(GradingTask.id).all()

def get_sample_responses(question_id):
    return session.query(QuestionResponse).filter_by(sample=1).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.id).all()

def get_grade(stuid, hw_id):
    return session.query(Grade).filter_by(stuid=stuid).\
        filter_by(hw_id=hw_id).first()

def add_grade(student, homework, score, excused=False):
    grade = Grade(student=student, homework=homework, 
                  score=score, excused=excused)
    session.add(grade)
    session.commit()
    
def get_user(stuid):
    return session.query(User).filter_by(stuid=stuid).one()



