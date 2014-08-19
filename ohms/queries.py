"""
queries.py

Some useful sql queries.
"""

from datetime import datetime
from collections import defaultdict

from base import session
from objects import QuestionResponse, GradingTask, User
from objects import Homework, Question, PeerReview, Grade
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
    qrs = session.query(QuestionResponse).\
        filter_by(stuid=stuid).\
        filter_by(question_id=question_id).\
        order_by(QuestionResponse.time).all()
    return qrs[-1] if qrs else None

def grading_permissions_query(question_id, stuid):
    return session.query(GradingTask.permission).\
        filter_by(stuid=stuid).\
        filter_by(question_id=question_id)

def get_grading_permissions(question_id, stuid):
    return grading_permissions_query(question_id, stuid).all()

def set_grading_permissions(question_id, stuid, permissions):
    grading_permissions_query(question_id, stuid).update({"permissions": permissions})
    session.commit()

def get_grading_task(grading_task_id):
    return session.query(GradingTask).get(grading_task_id)

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

def get_grade(stuid, assignment):
    grades = session.query(Grade).filter_by(student=stuid).\
        filter_by(assignment=assignment).all()
    return grades[0] if grades else None

def add_grade(student, assignment, time, score, points):
    grade = Grade(student=student, assignment=assignment, 
                  time=time, score=score, points=points)
    session.add(grade)
    session.commit()
    
def get_user(stuid):
    return session.query(User).filter_by(stuid=stuid).one()



