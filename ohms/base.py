"""
base.py

A base file for sqlalchemy to avoid cyclic imports
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import options

Base = declarative_base()
if options.test:
    engine = create_engine('sqlite:////afs/ir/class/stats60/db/test.db', echo=False)
else:
    engine = create_engine('sqlite:////afs/ir/class/stats60/db/prod.db', echo=False)

Session = sessionmaker(bind=engine)
session = Session()
