"""
grading_assignments.py
"""

import sys
import random

from base import session
from objects import User, GradingTask, GradingPermission
from queries import get_recent_question_responses, get_long_answer_qs
from datetime import datetime, timedelta


def make_grading_assignments(q_id, sunets):
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
        gp = GradingPermission(sunet=r.sunet, question_id=q_id,
                               permissions=0,
                               due_date=r.question.homework.due_date + timedelta(days=3))
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


def make_grader_assignments(q_id):
    """Assigns graders to grade the given question id"""

    responses = get_recent_question_responses(q_id)
    graders = session.query(User).filter_by(type="grader").all()

    for grader in graders:
        gp = GradingPermission(sunet=grader.sunet, question_id=q_id,
                               permissions=0,
                               due_date=datetime(2015, 1, 1, 0, 0, 0))
        session.add(gp)

        random.shuffle(responses)
        for response in responses:
            gt = GradingTask(grader=grader.sunet, question_response=response)
            session.add(gt)

    session.commit()


def make_admin_assignments(q_id):
    """Assigns admins permissions so they can view sample responses"""

    responses = get_recent_question_responses(q_id)
    admins = session.query(User).filter_by(type="admin").all()

    for admin in admins:
        gp = GradingPermission(sunet=admin.sunet, question_id=q_id,
                               permissions=0,
                               due_date=datetime(2015, 1, 1, 0, 0, 0))
        session.add(gp)

    session.commit()



def selective_peer_grading(hw_id, hw_number):

    treatments = {
        0: [1,1,1,0,0,1,1,0,0],
        1: [1,0,0,1,1,0,0,1,1],
        2: [1,1,1,0,0,0,0,1,1],
        3: [1,0,0,1,1,1,1,0,0]
        }

    groups = []
    for i in range(4):
        if treatments[i][hw_number-1]==1:
            groups.append(i)

    users = session.query(User).filter((User.group == groups[0]) | (User.group == groups[1])).all()
    sunets = [user.sunet for user in users]

    # XXX: Make sure all homework questions you want graded are composed of a
    # single Item, with a "Long Answer" type
    questions = get_long_answer_qs(hw_id)
    for q in questions:
        make_grading_assignments(q.id, sunets)
        make_grader_assignments(q.id)
        make_admin_assignments(q.id)


if __name__ == "__main__":
    selective_peer_grading(int(sys.argv[1]), int(sys.argv[2]))
