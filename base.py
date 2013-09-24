"""
base.py

A base file for sqlalchemy to avoid cyclic imports
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
engine = create_engine('sqlite:////afs/ir/class/stats60/ohms/ohms.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()
