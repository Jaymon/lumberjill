from __future__ import absolute_import

import collections
from datetime import datetime
import hashlib
import logging


class TimeValues(object):
    SECONDS_IN_MINUTE = 60
    SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE
    SECONDS_IN_DAY = 24 * SECONDS_IN_HOUR


class AndFilter(object):
    """
    A collection of filters that are processed like a logical 'and' operation.
    The filters are ordered by the keywords used in the constructor
    (an annoyance of working with logging.config.dictConfig). This uses short-
    circuiting logic, so if a filter returns False it will not process any
    remaining filters.
    """
    def __init__(self, **kwargs):
        self.filters = []
        keys = kwargs.keys()
        keys.sort()
        for k in keys:
            self.filters.append(kwargs[k])

    def filter(self, record):
        for f in self.filters:
            if not f.filter(record):
                return False
        return True

class FrequencyFilter(object):
    """
    Filters all records except the 1st, 10th, 100th, and all multiples of 1000
    for each unique message. Metadata is cleared every day.
    """

    def __init__(self, exception_types, exception_frequency):
        self.counter = collections.Counter()
        self.last_cleared_date = self._get_date_key()
        self.exception_types = exception_types
        self.exception_frequency = exception_frequency

    def filter(self, record):
        if self._should_clear():
            self._clear()

        cls = self._get_exception_match(record)
        record.key = self._get_key(record, cls)
        self.counter[record.key] += 1
        record.count = self.counter[record.key]
        should_log = self._should_log(record.count, cls)
        return should_log

    def _should_log(self, count, cls=None):
        """
        If this is an exception log record it will filter every log record
        except every 10th occurrence. Otherwise this filters all log records
        except the 1st, 10th, 100th, and every 1000th record.
        """
        if cls:
            return not count % self.exception_frequency
        else:
            return (count == 1 or
                    count == 10 or
                    count == 100 or
                    (count % 1000) == 0)

    def _get_key(self, record, cls=None):
        if cls:
            return "{}.{}".format(
                cls.__name__,
                hashlib.md5("{}.{}".format(
                    record.pathname,
                    record.lineno,
                )).hexdigest())
        else:
            return hashlib.md5("{}.{}.{}".format(
                record.levelname,
                record.pathname,
                record.lineno,
            )).hexdigest()

    def _should_clear(self):
        return self._get_date_key() != self.last_cleared_date

    def _clear(self):
        self.counter = collections.Counter()
        self.last_cleared_date = self._get_date_key()

    def _get_date_key(self):
        now = datetime.utcnow()
        return now.strftime("%Y-%m-%d")

    def _get_exception_match(self, record):
        if record.exc_info:
            exc_type = record.exc_info[0]
            for cls in self.exception_types:
                if issubclass(exc_type, cls):
                    return cls

        return None


class ProcessTimeFilter(object):
    """
    This class provides a filter that limits a process to logging a limited
    amount of messages over a specified period of time.
    """

    def __init__(self, period, limit):
        """
        Initialize

        period -- time period for window (in seconds)
        limit -- number of log messages allowed during specified period
        """
        self.period = period
        self.limit = limit
        self.processes = {}

    def filter(self, record):
        if record.process not in self.processes:
            self.processes[record.process] = _TimeWindow(self.period, self.limit)
        should_log = self.processes[record.process].add(record.created)
        return should_log


class LambdaFilter(object):
    """
    Simple filter that employs a single provided lambda function.
    """
    def __init__(self, f):
        self.f = f

    def filter(self, record):
        return self.f(record)


class _TimeWindow(object):
    """
    A floating window used for limiting the rate of acceptance over a period
    of time.

    A floating window with a user-defined limit and period. The add method
    returns True if an element is successfully added. New times are added if
    the length of the window is less than the limit, or if the difference
    between the first time and the new time is greater than the user-specified
    period. If adding a new element makes the length of the window greater
    than the limit then the first element of the window is removed.
    """

    def __init__(self, period, limit):
        """
        Initialize

        period -- time period for window (unit agnostic)
        limit -- number of log messages allowed during specified period
        """
        self.period = period
        self.limit = limit
        self.window = collections.deque()

    def add(self, time):
        """
        Returns True if the time was added to the window.
        """
        if len(self.window) < self.limit:
            self.window.append(time)
            return True

        else:
            if time - self.window[0] > self.period:
                self.window.popleft()
                self.window.append(time)
                return True

        return False
