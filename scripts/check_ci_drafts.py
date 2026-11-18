#!/usr/bin/env python3
"""CI adapter: an intentionally empty drafts queue is N/A, not validated.

README.md and drafts/README.md document that all existing drafts were processed.
Keep validate_skill.py's zero-target failure unchanged for direct callers.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def check(root=ROOT, run=subprocess.run):
    drafts = root / 'drafts'
    if not drafts.is_dir() or not (drafts / 'README.md').is_file():
        print('BLOCK: drafts/README.md 缺失，不能當成合法空佇列。')
        return 1
    targets = list((drafts / 'skills').glob('*/SKILL.md'))
    if not targets:
        print('NOT_APPLICABLE: 草稿 0 支，沒有草稿可驗；不是草稿驗證通過。')
        return 0
    return run([sys.executable, str(root / 'scripts' / 'validate_skill.py'), '--drafts'], cwd=root).returncode


if __name__ == '__main__':
    raise SystemExit(check())
