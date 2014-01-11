"""
grading_assignments.py
"""

import sys
import random

from base import session
from objects import Homework, User, GradingTask, GradingPermission
from queries import get_recent_question_responses, get_long_answer_qs, get_last_homework
from datetime import datetime, timedelta


def make_grading_assignments(q_id, sunets, due_date=None):
    """
    Assigns students in "sunets" to grade each other.

    Note that students who didn't respond to a question q_id will not be
    asked to grade their peers on this question.
    """

    responses = get_recent_question_responses(q_id)
    responses = [r for r in responses if r.sunet in sunets]
    random.shuffle(responses)

    # Create grading permissions
    for r in responses:
        if due_date is None:
            due_date = r.question.homework.due_date + timedelta(days=3)  # XXX ie Tuesday 9AM!
        gp = GradingPermission(sunet=r.sunet, question_id=q_id,
                               permissions=1,
                               due_date=due_date)
        session.add(gp)

    # This scheme guarantees that no pair of students is ever assigned to grade
    # together more than once.
    n = len(responses)
    for i, response in enumerate(responses):
        for offset in [1, 3, 6]:
            to_grade = responses[(i + offset) % n]
            gt = GradingTask(grader=response.sunet, question_response=to_grade)
            session.add(gt)

    session.commit()


def make_grader_assignments(q_id, sunets):
    """Assigns graders and admins to grade the given question id"""

    responses = get_recent_question_responses(q_id)
    responses = [r for r in responses if r.sunet in sunets]

    graders = session.query(User).filter_by(type="grader").all()
    graders += session.query(User).filter_by(type="admin").all()
    for grader in graders:
        gp = GradingPermission(sunet=grader.sunet, question_id=q_id,
                               permissions=1,
                               due_date=datetime(2015, 1, 1, 0, 0, 0))
        session.add(gp)

        random.shuffle(responses)
        for response in responses:
            gt = GradingTask(grader=grader.sunet, question_response=response)
            session.add(gt)

    session.commit()


def make_all_grading_assignments():

    treatments = {
        0: [1,1,1,0,0,1,1,0,0],
        1: [1,0,0,1,1,0,0,1,1],
        2: [1,1,1,0,0,0,0,1,1],
        3: [1,0,0,1,1,1,1,0,0]
        }

    homework = get_last_homework()
    hw_id = homework.id

    # Commenting out for the first week; just take all students.
    """
    groups = []
    for i in range(4):
        if treatments[i][hw_number-1]==1:
            groups.append(i)
    users = session.query(User).filter((User.group == groups[0]) | (User.group == groups[1])).all()
    """

    users = session.query(User).all()
    sunets = [user.sunet for user in users]

    # XXX: Make sure all homework questions you want graded are composed of a
    # single Item, with a "Long Answer" type
    questions = get_long_answer_qs(hw_id)
    for q in questions:
        make_grading_assignments(q.id, sunets)
        make_grader_assignments(q.id, sunets)


if __name__ == "__main__":
    make_all_grading_assignments()
