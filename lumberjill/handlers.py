from email.mime.text import MIMEText
import collections
import datetime
import logging
import socket


class EmailHandler(logging.Handler):
    """
    Logging handler that will send an informative email when a logging record is emitted.
    """
    def __init__(self, mailer, fromaddr, toaddrs, historylen):
        """
        Initialize.

        :param mailer: Email client that sends the email. See common.logging.emailclients
        :param fromaddr: Email address as a string.
        :param toaddrs: List of email addresses as strings.
        :param historylen: The email body will contain this number of the previous log statements.
        """
        super(EmailHandler, self).__init__()
        self.mailer = mailer
        self.fromaddr = fromaddr
        self.toaddrs = "; ".join(toaddrs)
        self.history = collections.deque(maxlen=historylen)

    def emit(self, record):
        """
        record -- LogRecord() -- https://docs.python.org/2/library/logging.html#logrecord-attributes
        """
        email = MIMEText(self._createbody(record))
        email['Subject'] = self._createsubject(record)
        email['From'] = self.fromaddr
        email['To'] = self.toaddrs

        try:
            self.mailer.send(email)
        except Exception as e:
            self.handleError(record)

    def handle(self, record):
        # format() must be called on the record in order to set the record.message attribute.
        msg = self.format(record)
        super(EmailHandler, self).handle(record)
        self.history.append(msg)

    def _createsubject(self, record):
        """
        This method should be overridden to customize the subject of the email.
        """
        datestamp = self._get_datestamp(record, '%Y-%m-%d %H:%M:%S')
        return "(Seen {} times) {} - [{}] - {}".format(
            record.count if hasattr(record, 'count') else '?',
            record.message,
            record.levelname,
            datestamp
        )

    def _createbody(self, record):
        """
        This method should be overridden to customize the body of the email.
        """
        body = []
        body.append("hostname: {}".format(socket.gethostname()))
        body.append("fqdn: {}".format(socket.getfqdn()))
        body.append(self._get_datestamp(record, datefmt='%A, %B %d, %Y at %H:%M:%S'))
        body.append("Record level: {}".format(record.levelname))
        body.append("Record name: {}".format(record.name))
        body.append("Record path: {}".format(record.pathname))
        body.append("module: {}".format(record.module))
        body.append("Process name and pid: {} [{}]".format(record.processName, record.process))
        body.append("")
        body.extend(self.history)
        body.append("")
        body.append(self.format(record))

        return "\n".join(body)

    def _get_datestamp(self, record, datefmt):
        dt = datetime.datetime.fromtimestamp(record.created)
        return dt.strftime(datefmt)
