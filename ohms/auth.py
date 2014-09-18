"""
auth.py

Abstracted out authorization routines.
"""
import options, os
from objects import session, User
from queries import get_user

def auth():
    if target == "local":
        stuid = "test"
        name = "Test User"
    else:
        stuid = os.environ.get("WEBAUTH_USER")
        name = os.environ.get("WEBAUTH_LDAP_DISPLAYNAME")
    return stuid, name

def validate_user():

    stuid, name = auth()

    try:
        user = get_user(stuid)
    except:
        type = "admin" if stuid in options.admins else "student"
        user = User(stuid=stuid,
                    name=name,
                    type=type)
        session.add(user)
        session.commit()

    if user.type == "admin" and user.proxy:
        user = session.query(User).get(user.proxy)

    return user

def validate_admin():

    stuid, name = auth()

    user = get_user(stuid)
    if not user.type == "admin":
        if user.stuid in options.admins:
            session.query(User).filter_by(stuid=user.stuid).update({
                "type": "admin"
            })
            session.commit()
        else:
            raise Exception("You are not authorized to view this page.")
    return user
