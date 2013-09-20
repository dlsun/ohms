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
    session.add_all([naftali, dennis, sample_sam])
    session.commit()

if __name__ == "__main__":
    init_db()
