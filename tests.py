#!/usr/bin/env python

from __future__ import absolute_import

import logging
import unittest

from lumberjill import filters


class StubFilter(object):
    def __init__(self, on=True):
        self.on = on
        self.hit = 0

    def filter(self, record):
        self.hit = self.hit + 1
        return self.on

class StubHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.recordsLogged = 0

    def emit(self, record):
        self.recordsLogged = self.recordsLogged + 1


class StubRecord():
    def __init__(self, exc_info=[], lineno=42, created=1, pathname='/', process='1',
            levelno=logging.WARN):
        self.exc_info = exc_info
        self.levelno = levelno
        self.levelname = logging.getLevelName(levelno)
        self.lineno = lineno
        self.created = created
        self.pathname = pathname
        self.process = process


class TestLoggingStuff(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_and_filter(self):
        f1 = StubFilter(on=True)
        f2 = StubFilter(on=False)

        filter = filters.AndFilter(a=f1, b=f2)
        handler = StubHandler()
        handler.addFilter(filter)

        # Hits both filters, but does not log the record
        handler.handle(StubRecord())
        self.assertEqual(1, f1.hit)
        self.assertEqual(1, f2.hit)
        self.assertEqual(0, handler.recordsLogged)

        # Hits only first filters, and does not log the record
        f1.on = False
        handler.handle(StubRecord())
        self.assertEqual(2, f1.hit)
        self.assertEqual(1, f2.hit)
        self.assertEqual(0, handler.recordsLogged)

        # Hits both filters, and logs the record
        f1.on = True
        f2.on = True
        handler.handle(StubRecord())
        self.assertEqual(3, f1.hit)
        self.assertEqual(2, f2.hit)
        self.assertEqual(1, handler.recordsLogged)

    def test_lambda_filter(self):
        handler = StubHandler()
        handler.addFilter(filters.LambdaFilter(lambda r: r.levelno >= logging.ERROR))

        levels = [logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARN, logging.ERROR,
            logging.CRITICAL, logging.FATAL]
        records = (StubRecord(levelno=level) for level in levels)
        for record in records:
            handler.handle(record)

        self.assertEquals(3, handler.recordsLogged)

    def test_time_window(self):
        tw = filters._TimeWindow(period=10, limit=2)

        self.assertTrue(tw.add(0))
        self.assertTrue(tw.add(1))
        for x in xrange(2,11):
            self.assertFalse(tw.add(x))
        self.assertTrue(tw.add(11))
        self.assertTrue(tw.add(12))
        for x in xrange(13,20):
            self.assertFalse(tw.add(x))

    def test_process_time_filter(self):
        handler = StubHandler()
        handler.addFilter(filters.ProcessTimeFilter(period=10, limit=2))

        #Generator will create 50 records for each process for times 0-49
        records = (StubRecord(created=t/2, process=str(t%2)) for t in range(100))
        for record in records:
            handler.handle(record)

        self.assertEquals(20, handler.recordsLogged)

    def test_frequency_filter(self):
        handler = StubHandler()
        handler.addFilter(filters.FrequencyFilter([ZeroDivisionError], 10))

        # Generator will create 5000 records
        records = (StubRecord() for t in xrange(5000))
        for record in records:
            handler.handle(record)

        # Should log records for 1, 10, 100, and {1-5}000
        self.assertEquals(8, handler.recordsLogged)

        #Generator will create 2 unique records 50 times each
        err = ZeroDivisionError()
        records = (StubRecord(created=t/2, lineno=str(t%2), exc_info=(type(err), err, None)) for t in range(100))
        for record in records:
            handler.handle(record)

        # Should log 10 times, plus the 8 previous
        self.assertEquals(18, handler.recordsLogged)

if __name__ == '__main__':
    unittest.main()
