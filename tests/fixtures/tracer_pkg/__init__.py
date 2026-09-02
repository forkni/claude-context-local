"""Fixture package with known call edges for ``evaluation.tracer`` tests.

Line numbers matter: ``test_collector.py`` reads this package's source to
derive expected ``def_line``/``body_line`` values, so edit freely but keep
each construct's shape (decorated def, multi-line signature, and so on).
"""
