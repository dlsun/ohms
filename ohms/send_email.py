"""
email.py

Tools for sending emails.
"""


# XXX: This doesn't appear to work on corn, perhaps only works from the web
# servers, because can't connect to localhost. Fuck an A, amiright?

import smtplib

def send_all(users, subject, message):
    """Message should have a '%s' for their name"""

    smtpObj = smtplib.SMTP('localhost')
    sender = 'stats60-spr1314-staff@lists.stanford.edu'

    for user in users:
        name = user.name
        email = "%s@stanford.edu" % user.stuid
        
        msg = "\n".join(["From: Stats 60 Staff <%s>" % sender,
                         "To: %s <%s>" % (name, email),
                         "Subject: %s" % subject,
                         "",
                         message % name])

        smtpObj.sendmail(sender, [email], msg)
