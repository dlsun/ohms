"""
base.py

A base file for sqlalchemy to avoid cyclic imports
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from options import get_db

Base = declarative_base()
engine = create_engine(get_db(), echo=False)

Session = sessionmaker(bind=engine)
session = Session()
