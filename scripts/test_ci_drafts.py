#!/usr/bin/env python3
"""Regression checks for the CI-only empty-drafts adapter."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock
import check_ci_drafts as C


class DraftsCI(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'drafts').mkdir()
        (self.root / 'drafts' / 'README.md').write_text('Intentionally empty queue')
        self.run = Mock(return_value=SimpleNamespace(returncode=0))

    def add_draft(self):
        p = self.root / 'drafts' / 'skills' / 'example'
        p.mkdir(parents=True)
        (p / 'SKILL.md').write_text('draft')

    def test_empty_is_explicit_na_not_validation(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(C.check(self.root, self.run), 0)
        self.assertIn('NOT_APPLICABLE', output.getvalue())
        self.run.assert_not_called()

    def test_nonempty_calls_original_validator(self):
        self.add_draft()
        self.assertEqual(C.check(self.root, self.run), 0)
        self.run.assert_called_once_with([C.sys.executable, str(self.root / 'scripts' / 'validate_skill.py'), '--drafts'], cwd=self.root)

    def test_validator_failures_propagate(self):
        self.add_draft()
        for code in (1, 2):
            self.run.return_value.returncode = code
            self.assertEqual(C.check(self.root, self.run), code)

    def test_missing_marker_fails_closed(self):
        (self.root / 'drafts' / 'README.md').unlink()
        self.assertEqual(C.check(self.root, self.run), 1)
        self.run.assert_not_called()

    def test_missing_drafts_fails_closed(self):
        (self.root / 'drafts' / 'README.md').unlink()
        (self.root / 'drafts').rmdir()
        self.assertEqual(C.check(self.root, self.run), 1)
        self.run.assert_not_called()


if __name__ == '__main__':
    main()
