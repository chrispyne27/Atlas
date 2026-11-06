#!/usr/bin/env python3
"""Focused integrity checks for the v1 schema contract, not runtime acceptance."""
import pathlib
import sqlite3
import unittest

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / 'atlas_engine/storage/schema-v1.sql'

class SchemaChecks(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.executescript(SCHEMA.read_text())
        self.db.execute("INSERT INTO repository VALUES ('r','local:test')")
        for s in ('linux', 'rtos'):
            self.db.execute('INSERT INTO snapshot VALUES (?,?,?,?,?,?,?,?,?,?)',
                (s,'r','revision',s,'manifest','toolchain','test',1,'staging','now'))
            self.db.execute('INSERT INTO artifact VALUES (?,?,?,?)',(s,'shared.cpp','hash','authored'))
            self.db.execute('INSERT INTO build_target VALUES (?,?,?,?)',(s,'app','app','application'))
            self.db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',(s,'ev','compiler','shared.cpp',1,'test','{}'))
        self.db.execute("INSERT INTO entity VALUES ('linux','symbol','symbol','global','usr','method')")

    def test_multiple_commands_preserved(self):
        for n in ('a','b'):
            self.db.execute('INSERT INTO compilation VALUES (?,?,?,?,?,?,?)',
                ('linux',n,'app','shared.cpp',n,'["c++"]','parsed'))
        self.assertEqual(self.db.execute('SELECT count(*) FROM compilation').fetchone()[0],2)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO compilation VALUES ('linux','c','app','shared.cpp','a','[]','parsed')")

    def test_cross_snapshot_relation_rejected(self):
        self.db.execute("INSERT INTO entity VALUES ('rtos','other','symbol','global','other','other')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO relation VALUES ('linux','bad','symbol','other',NULL,'calls','resolved',NULL,'ev')")

    def test_unresolved_retained_and_false_resolution_rejected(self):
        self.db.execute("INSERT INTO relation VALUES ('linux','unknown','symbol',NULL,'virtualMethod','calls','unresolved',NULL,'ev')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE relation SET resolution='resolved' WHERE id='unknown'")
        self.assertEqual(self.db.execute('SELECT resolution FROM relation').fetchone()[0],'unresolved')

    def test_requirement_ids_are_scoped(self):
        for scope in ('component-a','component-b'):
            self.db.execute('INSERT INTO entity VALUES (?,?,?,?,?,?)',('linux',scope,'requirement',scope,'REQ-001','Requirement'))
        self.assertEqual(self.db.execute("SELECT count(*) FROM entity WHERE external_key='REQ-001'").fetchone()[0],2)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__ == '__main__':
    unittest.main()
