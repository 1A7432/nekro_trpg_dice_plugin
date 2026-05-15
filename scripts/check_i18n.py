#!/usr/bin/env python3
"""i18n validation script for nekro_trpg_dice_plugin."""

import os
import glob
import re
import sys

errors = []

# 1. Check .po and .mo sync
print("=== Checking .po/.mo sync ===")
po_files = glob.glob('trpg_dice/locale/*/LC_MESSAGES/trpg_dice.po')
for po in po_files:
    mo = po.replace('.po', '.mo')
    if not os.path.exists(mo):
        errors.append(f"MISSING: {mo}")
    else:
        po_time = os.path.getmtime(po)
        mo_time = os.path.getmtime(mo)
        if po_time > mo_time:
            errors.append(f"STALE: {mo} is older than {po}")
        else:
            print(f"OK: {mo}")

# 2. Check for _(f'...') anti-pattern
print("\n=== Checking _(f'...') anti-pattern ===")
found = False
for root, dirs, files in os.walk('trpg_dice'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fp:
                lines = fp.readlines()
            for i, line in enumerate(lines, 1):
                if '_(f' in line and 'WRONG' not in line:
                    errors.append(f"ANTI-PATTERN: {path}:{i}: {line.strip()}")
                    found = True
if not found:
    print("OK: No _(f'...') anti-patterns found")

# 3. Check placeholder consistency in .po files
print("\n=== Checking placeholder consistency ===")
import subprocess
result = subprocess.run(
    [sys.executable, '-m', 'unittest', 'tests.test_i18n.I18nTests.test_placeholder_consistency', '-v'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("OK: Placeholder consistency test passed")
else:
    errors.append("Placeholder consistency test FAILED")
    print(result.stdout)
    print(result.stderr)

# Report
print("\n=== Summary ===")
if errors:
    print(f"FAILED: {len(errors)} issue(s) found:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("PASSED: All i18n checks passed")
    sys.exit(0)
