# DOC-MVSEL2-HARDEN1-V3 pre-qualification bootstrap for Codex

Run this on the user's workstation while acting as `software-implementation`. Do not run qualification checks until it succeeds.

```bash
set -euo pipefail

CANDIDATE=a9cb41ad9b1c6305de195f1a88b71ea098e582b7
WORKPLAN=workplans/active/DOC-MVSEL2_HARDEN1_V3.md
WORKPLAN_SHA=ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b
TEMPLATE=workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.template.md
HANDOFF=workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md
IDENTITY=workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json
COORD_REF=feat/mvsel2-forward-lazy

git checkout --detach "$CANDIDATE"
test "$(git rev-parse HEAD)" = "$CANDIDATE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
test "$(sha256sum "$WORKPLAN" | awk '{print $1}')" = "$WORKPLAN_SHA"

mkdir -p qualification/evidence qualification/tmp
conda run -n mace python scripts/mvsel2_harden1_v3_candidate_identity.py --manifest "$IDENTITY"
DIGEST=$(conda run -n mace python -c 'import json; print(json.load(open("workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json"))["candidate_content_identity"])' | tail -n 1)
test -n "$DIGEST"
export DIGEST

git show "$COORD_REF:$TEMPLATE" > "$HANDOFF"
conda run -n mace python -c 'from pathlib import Path; import os; p=Path("workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md"); s=p.read_text(); token="__CANDIDATE_CONTENT_IDENTITY__"; assert s.count(token)==1; p.write_text(s.replace(token, os.environ["DIGEST"]))'
HANDOFF_SHA=$(sha256sum "$HANDOFF" | awk '{print $1}')
printf 'candidate_content_identity=%s\nqualification_handoff_sha256=%s\n' "$DIGEST" "$HANDOFF_SHA"
```

Then verify the implementation-owned boundary:

```bash
grep -F "$DIGEST" "$HANDOFF"
git diff --exit-code -- . \
  ':(exclude)workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json' \
  ':(exclude)workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md'
git status --porcelain=v1 --untracked-files=all
```

Expected post-bootstrap changes are limited to the two generated `workplans/active/` coordination files and declared qualification output directories. If any product/test/spec/config/package/release path is modified, or any undeclared untracked/shadowing source exists, stop before qualification.

Record `HANDOFF_SHA`, then switch to `software-qualification` and consume only `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md`. Product source mutation is forbidden.
