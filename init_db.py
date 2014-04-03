"""
init_db.py

Initializes the database from scratch.
"""

from ohms.objects import *
import sys

def prod_init_db(file):

    from ohms.base import Base, session, engine

    Base.metadata.create_all(engine)
    homework = Homework()
    homework.from_xml(file)
    session.add(homework)
    session.commit()

def add_sample_responses(question_id):

    from ohms.queries import get_question
    question = get_question(question_id)

    ir = ItemResponse(
        item_id=question.items[0].id, 
        response="This is a test response.")
    qr = QuestionResponse(
        stuid="joeshmoe",
        time=datetime.now(),
        question_id=question_id,
        item_responses=[ir])
    session.add(qr)

    ir = ItemResponse(
        item_id=question.items[0].id, 
        response="This is another test response.")
    qr = QuestionResponse(
        stuid="janedoe",
        time=datetime.now(),
        question_id=question_id,
        item_responses=[ir])
    session.add(qr)

    gt = GradingTask(grader="jsmith",
                     student="joeshmoe",
                     question_id=question_id)
    session.add(gt)

    gt = GradingTask(grader="jsmith",
                     student="janedoe",
                     question_id=question_id)
    session.add(gt)

    gt = GradingTask(grader="jsmith",
                     student="jsmith",
                     question_id=question_id)
    session.add(gt)

    gt = GradingTask(grader="joeshmoe",
                     student="jsmith",
                     question_id=question_id)
    session.add(gt)

    session.commit()


if __name__ == "__main__":
    prod_init_db(sys.argv[1])
