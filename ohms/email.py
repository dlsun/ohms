"""
email.py

Tools for sending emails.
"""

import smtplib

def send_all(users, subject, message):
    """Message should have a '%s' for their name"""

    smtpObj = smtplib.SMTP('localhost')
    sender = 'psych10-win1314-staff@lists.stanford.edu'

    for user in users:
        name = user.name
        email = "%s@stanford.edu" % user.sunet
        
        msg = "\n".join(["From: Stats 60 Staff <%s>" % sender,
                         "To: %s <%s>" % (name, email),
                         "Subject: %s" % subject,
                         "",
                         message % name])

        smtpObj.sendmail(sender, [email], msg)
