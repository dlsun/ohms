"""
assign_tasks.py
"""

import sys
from datetime import datetime, timedelta
import random

from base import session
from objects import User, Homework, Question, QuestionResponse, GradingTask, LongAnswerItem
from queries import get_last_question_response, get_last_due_homework
from send_email import send_all


def assign_tasks(hw_id, due_date):

    homework = session.query(Homework).get(hw_id)
    
    users = session.query(User).filter(User.type == "student").order_by(User.stuid).all()

    for q in homework.questions:
        # only if this is a peer graded question
        if not isinstance(q.items[0], LongAnswerItem):
            continue

        random.seed(q.id)  # setting a seed will be useful for debugging

        responsible_kids = list()   # did the homework!
        irresponsible_kids = list() # didn't do the homework!

        # Figure out who did the homework
        for user in users:
            if get_last_question_response(q.id, user.stuid):
                responsible_kids.append(user.stuid)
            else:
                irresponsible_kids.append(user.stuid)

        # Make the assignments for the responsible kids
        n = len(responsible_kids)
        random.shuffle(responsible_kids)
        for i, stuid in enumerate(responsible_kids):

            # Make the assignments for this responsible student
            for offset in [1, 3, 6]:
                j = (i + offset) % n
                gt = GradingTask(grader=stuid,
                                 student=responsible_kids[j],
                                 question_id=q.id)
                session.add(gt)

        # Make the assignments for the irresponsible kids:
        # Do so in round robin order, shuffling the responsible students again
        # to minimize the number of pairs of students grading together.
        random.shuffle(responsible_kids)
        for i, stuid in enumerate(irresponsible_kids):

            # Make the assignments for this irresponsible student
            for offset in range(3):
                j = (i * 3 + offset) % n
                gt = GradingTask(grader=stuid,
                                 student=responsible_kids[j],
                                 question_id=q.id)
                session.add(gt)

        # Make all self-assignments
        for stuid in (responsible_kids + irresponsible_kids):
            gt = GradingTask(grader=stuid,
                             student=stuid,
                             question_id=q.id)
            session.add(gt)

    session.commit()

    # Send email notifications to all the students
    send_all(users, "Peer Assessment for %s is Ready" % homework.name,
r"""Dear %s,

We've made the peer-grading assignments for this week. The assessments
are due {due_date}, and you can start after lecture today at 11:00AM.

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

Sincerely,
OHMS

P.S. This is an automatically generated message ;-)
""".format(due_date=due_date.strftime("%A, %b %d at %I:%M %p")))

    return r'''Successfully assigned %d students. You should have received an 
e-mail confirmation.''' % len(users)


def auto_assign():
    """Assignment for STATS 60, spring quarter"""

    # Determine the due date, which the next Tuesday at 5 PM.
    this_time = datetime.now()
    while this_time.weekday() != 1:  # 0 == Monday, 1 == Tuesday...
        this_time += timedelta(days=1) 
    due_date = datetime(this_time.year, this_time.month, this_time.day, 17, 0)

    # Determine the homework to assign, which is the last thing due.
    hw_id = get_last_due_homework().id
    
    print assign_tasks(hw_id, due_date)


if __name__ == "__main__":
    auto_assign()
