# DOC-MVSEL2-HARDEN1-V3 pre-qualification bootstrap for Codex

Run this while acting as `software-implementation`. Its only jobs are to establish the clean frozen candidate, compute/reuse its content identity, materialize the exact qualification driver and handoff from the coordination branch, validate them, and then switch roles. Do not execute Q1-Q8 until this succeeds.

```bash
set -euo pipefail

CANDIDATE=a9cb41ad9b1c6305de195f1a88b71ea098e582b7
WORKPLAN=workplans/active/DOC-MVSEL2_HARDEN1_V3.md
WORKPLAN_SHA=ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b
COORD_REF=feat/mvsel2-forward-lazy
TEMPLATE=workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.template.md
DRIVER_SRC=workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py
DRIVER=qualification/tmp/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py
DRIVER_BLOB_SHA=fe649742674ecdff7286452ced5ecf044402098e
HANDOFF=workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md
IDENTITY=workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json

git checkout --detach "$CANDIDATE"
test "$(git rev-parse HEAD)" = "$CANDIDATE"
test "$(sha256sum "$WORKPLAN" | awk '{print $1}')" = "$WORKPLAN_SHA"

STATUS=$(git status --porcelain=v1 --untracked-files=all)
if [ -n "$STATUS" ] && [ "$STATUS" != "?? $IDENTITY" ]; then
  printf '%s\n' "$STATUS" >&2
  echo 'unexpected dirty/untracked state before qualification bootstrap' >&2
  exit 2
fi

mkdir -p qualification/evidence qualification/tmp
if [ ! -f "$IDENTITY" ]; then
  conda run -n mace python scripts/mvsel2_harden1_v3_candidate_identity.py --manifest "$IDENTITY"
fi
DIGEST=$(conda run -n mace python -c 'import json; d=json.load(open("workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json")); assert d["candidate_commit"]=="a9cb41ad9b1c6305de195f1a88b71ea098e582b7"; assert d["policy_id"]=="mdstats.mvsel2-harden1-v3.candidate-identity.v1"; print(d["candidate_content_identity"])' | tail -n 1)
test -n "$DIGEST"

git show "$COORD_REF:$DRIVER_SRC" > "$DRIVER"
test "$(git hash-object "$DRIVER")" = "$DRIVER_BLOB_SHA"

git show "$COORD_REF:$TEMPLATE" > "$HANDOFF.tmp"
export DIGEST
conda run -n mace python - <<'PY'
from pathlib import Path
import os
src = Path('workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md.tmp')
dst = Path('workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md')
s = src.read_text(encoding='utf-8')
token = '__CANDIDATE_CONTENT_IDENTITY__'
if s.count(token) != 1:
    raise SystemExit(f'expected exactly one identity token, found {s.count(token)}')
s = s.replace(token, os.environ['DIGEST'])
if 'kind: qualification-handoff\n' not in s:
    raise SystemExit('handoff kind is not qualification-handoff')
if '__' in s or '<CAMPAIGN_DATABASE>' in s or '<DOMAIN>' in s:
    raise SystemExit('unresolved placeholder remains in handoff')
dst.write_text(s, encoding='utf-8')
src.unlink()
PY

HANDOFF_SHA=$(sha256sum "$HANDOFF" | awk '{print $1}')
printf 'candidate_content_identity=%s\nqualification_handoff_sha256=%s\nqualification_driver_blob_sha=%s\n' "$DIGEST" "$HANDOFF_SHA" "$DRIVER_BLOB_SHA"

grep -Fx 'kind: qualification-handoff' "$HANDOFF"
grep -F "candidate_content_identity: $DIGEST" "$HANDOFF"
! grep -E '__[A-Z0-9_]+__|<CAMPAIGN_DATABASE>|<DOMAIN>' "$HANDOFF"
test "$(git hash-object "$DRIVER")" = "$DRIVER_BLOB_SHA"
git diff --exit-code -- . \
  ':(exclude)workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json' \
  ':(exclude)workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md'
git status --porcelain=v1 --untracked-files=all
```

Expected post-bootstrap additions are limited to the two generated `workplans/active/` coordination files and declared `qualification/` outputs, including the exact driver copied to `qualification/tmp/`. No product/test/spec/config/package/release path may change.

After these checks pass, record `HANDOFF_SHA`, switch to `software-qualification`, and consume only `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md`. Product source mutation remains forbidden.
