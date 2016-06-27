import logging
import os

import mandrill
import sendgrid

# Prevent infinite logging loops. If the user wants the log messages, then
# this logger can be given a proper handler.
logger = logging.getLogger(__name__)
logger.propagate = False
logger.addHandler(logging.NullHandler())


class MandrillEmail(object):
    """
    This implementation uses Mandrill to send email.
    """
    def __init__(self, api_key):
        """
        Initialize email client.

        param api_key: Mandrill API Key
        """
        self._client = mandrill.Mandrill(api_key)

    def send(self, mime_email):
        """
        Sends the provided email. Checks the 'NOTIFY_EMAIL' environment
        variable to decide whether to actually send the email or to log it.

        :param mime_email: MIMEType email to be sent via Mandrill
        """
        message = {
            'from_email': mime_email['From'],
            'from_name': mime_email.from_name,
            'subject': mime_email['Subject'],
            'text': mime_email.get_payload(),
            'to': [{'email': mime_email['To'], 'type': 'to', 'name': ""}],
        }

        if bool(int(os.environ.get('NOTIFY_EMAIL', 0))):
            results = self._client.messages.send(message=message, async=False)
            logger.info("Results of sending email [{}]: {}".format(message['subject'], results))
        else:
            logger.info("NOTIFY_EMAIL is off. Didn't send this: " + _email_headers(mime_email))


class SendGridEmail(object):
    """
    This implementation uses SendGrid to send email.
    """
    def __init__(self, username, password):
        """
        Initialize email client.

        :param username: SendGrid username
        :param password: SendGrid password
        """
        self._client = sendgrid.SendGridClient(
            username,
            password,
            raise_errors=True
        )

    def send(self, mime_email):
        """
        Sends the provided email. Checks the 'NOTIFY_EMAIL' environment
        variable to decide whether to actually send the email or to log it.

        :param mime_email: MIMEType email to be sent via SendGrid
        """
        message = sendgrid.Mail(
            to=mime_email['To'],
            from_email=mime_email['From'],
            subject=mime_email['Subject'],
            text=mime_email.get_payload()
        )
        if bool(int(os.environ.get('NOTIFY_EMAIL', 0))):
            self._client.send(message)
            logger.info("Email sent: " + _email_headers(mime_email))
        else:
            logger.info("NOTIFY_EMAIL is off. Didn't send this: " + _email_headers(mime_email))


class StubEmailer(object):
    """
    A stub email client that just logs the provided email.
    """
    def __init__(self):
        pass

    def send(self, mime_email):
        """
        Logs the provided email message.

        :param mime_email: MIMEType email to be logged
        """
        logger.info("StubEmailer didn't send this: " + _email_headers(mime_email))


def _email_headers(msg):
    return "\n".join(
        ['',
         '     TO: ' + msg['To'],
         '     FROM: ' + msg['From'],
         '     SUBJECT: ' + msg['Subject']])

