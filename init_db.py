"""
init_db.py

Initializes the database from scratch.
"""

import os
import sys
import objects


def init_db():
    if os.path.exists("ohms.db"):
        if raw_input("Destroy the database??? (y/n)") == "y":
            os.remove("ohms.db")
        else:
            print "Aborting"
            sys.exit(-1)

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

    # fake homework response
    q_response1 = objects.QuestionResponse(sunet="naftali", question_id=2)
    i_response1 = objects.ItemResponse(question_response=q_response1,
                                       item_id=3,
                                       response="Fuck Bayesians, y'know?")

    # fake grading assignment
    grading1 = objects.GradingPermission(sunet="dlsun",
                                         question_id=2,
                                         permissions=1)

    session.add_all([naftali, dennis, sample_sam, q_response1, i_response1,
                     grading1])
    session.commit()

if __name__ == "__main__":
    init_db()
