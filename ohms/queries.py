"""
queries.py

Some useful sql queries.
"""

from collections import defaultdict

from base import session
from objects import QuestionResponse, QuestionGrade, GradingTask, GradingPermission, User
from objects import Homework, Question


def get_question_responses(id, sunet):
    return session.query(QuestionResponse).\
        filter_by(sunet=sunet).\
        filter_by(question_id=id).\
        order_by(QuestionResponse.time).all()


def get_recent_question_responses(q_id):
    """Returns each student's most recent response to a question"""
    responses = session.query(QuestionResponse).\
        filter_by(question_id=q_id).\
        join(User).\
        filter(User.type == "student").all()

    student_responses = defaultdict(list)
    for r in responses:
        student_responses[r.sunet].append(r)

    return [max(rs, key=lambda r: r.time) for rs in student_responses.values()]


def get_grading_permissions(question_id, sunet):
    return session.query(GradingPermission).\
        filter_by(sunet=sunet).join(Question).\
        filter_by(id=question_id).one()


def get_question_grades(grading_task_id, sunet):
    return session.query(QuestionGrade).\
        filter_by(grading_task_id=grading_task_id).\
        join(GradingTask).\
        filter(GradingTask.grader == sunet).\
        order_by(QuestionGrade.time).all()


def get_user(sunet):
    return session.query(User).filter_by(sunet=sunet).one()


def get_long_answer_qs(hw_id):
    """Returns questions that are composed of a single long answer"""
    questions = session.query(Question).\
        join(Homework).\
        filter_by(id=hw_id).all()

    return [q for q in questions if len(q.items) == 1 and
            q.items[0].type == "Long Answer"]
