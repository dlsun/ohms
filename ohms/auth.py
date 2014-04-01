"""
auth.py

Abstracted out authorization routines.
"""
import options, os

def auth_stuid():
    """Must return the student id, and guarantee that it's authorized."""

    if options.target == "local":
        return "jsmith"

    return os.environ.get("WEBAUTH_USER")


def auth_student_name():
    """Must return the student's name, and guarantee that it's authorized."""
    if options.target == "local":
        return "John Smith"

    return os.environ.get("WEBAUTH_LDAP_DISPLAYNAME")
