"""
init_db.py
Date: 2013-09-02
Author: Naftali Harris
"""

import os
import sys
import objects


def init_db():
    if os.path.exists("ohms.db"):
        print "Destroy the database and restart it??? (y/n)"
        if raw_input() == "y":
            os.remove("ohms.db")
        else:
            print "Aborting"
            sys.exit(-1)

    from base import Base, session, engine  # creates ohms.db

    Base.metadata.create_all(engine)
    h = objects.Homework()
    h.from_xml('hws/example.xml')
    session.add(h)
    session.commit()

if __name__ == "__main__":
    init_db()
