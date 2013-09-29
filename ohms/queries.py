"""
queries.py

Some useful sql queries.
"""

from collections import defaultdict
import sqlalchemy

from base import session
from objects import QuestionResponse, QuestionGrade, GradingTask, User


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


def get_question_grades(id, sunet):
    return session.query(QuestionGrade).\
        filter_by(grading_task_id=id).\
        join(GradingTask).\
        filter(GradingTask.grader == sunet).\
        order_by(QuestionGrade.time).all()


def get_user(sunet):
    return session.query(User).filter_by(sunet=sunet).one()


def exists_user(sunet):
    try:
        user = get_user(sunet)
        return True
    except sqlalchemy.orm.exc.NoResultFound:
        return False
