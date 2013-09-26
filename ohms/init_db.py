"""
init_db.py

Initializes the database from scratch.
"""

import os
import sys
import objects


def testing_init():
    from base import Base, session, engine  # creates ohms.db

    Base.metadata.create_all(engine)
    h = objects.Homework()
    h.from_xml('hws/example.xml')
    session.add(h)

    naftali = objects.User(sunet="naftali",
                           name="Naftali Harris",
                           type="admin")
    dennis = objects.User(sunet="dlsun",
                          name="Dennis Sun",
                          type="admin")

    # Create the fake sample user
    # His sunet is okay since real sunets have no spaces
    # Use type=sample for identifying sample submissions,
    sample_sam = objects.User(sunet="Sample Sam",
                              name="Sample Sam",
                              type="sample")


    session.add_all([naftali, dennis, sample_sam])

    # fake homework response
    q_response1 = objects.QuestionResponse(sunet="naftali", question_id=2)
    i_response1 = objects.ItemResponse(question_response=q_response1,
                                       item_id=3,
                                       response="Fuck Bayesians, y'know?")
    q_response2 = objects.QuestionResponse(sunet="dlsun",
                                           question_id=2,
                                           score=0,
                                           comments="")
    i_response2 = objects.ItemResponse(question_response=q_response2,
                                       item_id=3,
                                       response=r'''
Lorem ipsum dolor sit amet, consectetur adipisicing elit,
sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation
ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur
sint occaecat cupidatat non proident, sunt in culpa qui
officia deserunt mollit anim id est laborum.
''')
    q_response3 = objects.QuestionResponse(sunet="Sample Sam",
                                           question_id=2,
                                           score=20,
                                           comments="")
    i_response3 = objects.ItemResponse(question_response=q_response3,
                                       item_id=3,
                                       response="This is an example of a full-credit answer.")
    q_response4 = objects.QuestionResponse(sunet="Sample Sam",
                                           question_id=2,
                                           score=5,
                                           comments="")
    i_response4 = objects.ItemResponse(question_response=q_response4,
                                       item_id=3,
                                       response="This guy only deserves 5 points.")

    # fake grading assignment
    grading1 = objects.GradingPermission(sunet="dlsun",
                                         question_id=2,
                                         permissions=0)
    task1 = objects.GradingTask(grader="dlsun",
                                question_response=q_response1)
    task2 = objects.GradingTask(grader="dlsun",
                                question_response=q_response2)

    session.add_all([q_response1, i_response1,
                     q_response2, i_response2,
                     q_response3, i_response3,
                     q_response4, i_response4,
                     grading1, task1, task2])
    session.commit()


def prod_init_db():

    from base import Base, session, engine  # creates ohms.db

    Base.metadata.create_all(engine)
    h = objects.Homework()
    h.from_xml('hws/hw1.xml')
    session.add(h)

    naftali = objects.User(sunet="naftali",
                           name="Naftali Harris",
                           type="admin")
    dennis = objects.User(sunet="dlsun",
                          name="Dennis Sun",
                          type="admin")

    # Create the fake sample user
    # His sunet is okay since real sunets have no spaces
    # Use type=sample for identifying sample submissions,
    sample_sam = objects.User(sunet="Sample Sam",
                              name="Sample Sam",
                              type="sample")


    session.add_all([naftali, dennis, sample_sam])
    session.commit()

if __name__ == "__main__":
    prod_init_db()
