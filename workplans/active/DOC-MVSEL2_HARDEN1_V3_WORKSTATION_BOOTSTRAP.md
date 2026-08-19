# DOC-MVSEL2-HARDEN1-V3 pre-qualification bootstrap for Codex

Run this on the user's workstation while acting as `software-implementation`. Do not run Q1-Q8 until this bootstrap succeeds and emits an exact bound handoff.

The bootstrap supports the current partially-completed state where the candidate identity JSON already exists as the only untracked file.

## 1. Establish/validate the frozen candidate and identity

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
test "$(sha256sum "$WORKPLAN" | awk '{print $1}')" = "$WORKPLAN_SHA"

STATUS=$(git status --porcelain=v1 --untracked-files=all)
if [ -n "$STATUS" ] && [ "$STATUS" != "?? $IDENTITY" ]; then
  printf '%s\n' "$STATUS" >&2
  echo 'unexpected dirty/untracked state before handoff binding' >&2
  exit 2
fi

mkdir -p qualification/evidence qualification/tmp
if [ ! -f "$IDENTITY" ]; then
  conda run -n mace python scripts/mvsel2_harden1_v3_candidate_identity.py --manifest "$IDENTITY"
fi

DIGEST=$(conda run -n mace python -c 'import json; d=json.load(open("workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json")); assert d["candidate_commit"]=="a9cb41ad9b1c6305de195f1a88b71ea098e582b7"; assert d["policy_id"]=="mdstats.mvsel2-harden1-v3.candidate-identity.v1"; print(d["candidate_content_identity"])' | tail -n 1)
test -n "$DIGEST"
```

## 2. Bind the real production invocation

Before generating the handoff, Codex must identify the workstation's already-established production campaign database/domain and the exact existing commands used for the two campaign-path checks. Do not invent or alter scientific/resource configuration.

Set these four shell variables to literal values from the existing production workflow:

```bash
export MVSEL2_CAMPAIGN_DATABASE='/absolute/path/to/the/real/production/campaign.sqlite'
export MVSEL2_DOMAIN='the_exact_production_domain'
export MVSEL2_Q5_COMMAND='the exact existing production MVSEL2/MVSTATE2 selector-continuation command'
export MVSEL2_Q7_COMMAND='the exact existing StageResourceScope-wrapped production campaign command'
```

Requirements:

- `MVSEL2_CAMPAIGN_DATABASE` exists and is the real 36,408-candidate / 165-family production campaign database;
- `MVSEL2_DOMAIN` is the exact domain used with that database;
- Q5 is the pre-existing production selector/checkpoint-resume invocation, not a newly invented fixture command;
- Q7 is the pre-existing campaign invocation that actually traverses the `StageResourceScope` integration path;
- if any of these cannot be established from the workstation's existing production workflow/configuration, stop with `BLOCKED` rather than emitting a handoff.

## 3. Generate and validate the exact handoff

```bash
export DIGEST TEMPLATE HANDOFF COORD_REF

test -f "$MVSEL2_CAMPAIGN_DATABASE"
test -n "$MVSEL2_DOMAIN"
test -n "$MVSEL2_Q5_COMMAND"
test -n "$MVSEL2_Q7_COMMAND"
export MVSEL2_CAMPAIGN_DATABASE MVSEL2_DOMAIN MVSEL2_Q5_COMMAND MVSEL2_Q7_COMMAND

git show "$COORD_REF:$TEMPLATE" > "$HANDOFF.tmp"
conda run -n mace python - <<'PY'
from pathlib import Path
import os

src = Path('workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md.tmp')
dst = Path('workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md')
s = src.read_text(encoding='utf-8')
replacements = {
    '__CANDIDATE_CONTENT_IDENTITY__': os.environ['DIGEST'],
    '__CAMPAIGN_DATABASE__': os.environ['MVSEL2_CAMPAIGN_DATABASE'].replace("'", "'\"'\"'"),
    '__DOMAIN__': os.environ['MVSEL2_DOMAIN'].replace("'", "'\"'\"'"),
    '__Q5_PRODUCTION_COMMAND__': os.environ['MVSEL2_Q5_COMMAND'],
    '__Q7_PRODUCTION_COMMAND__': os.environ['MVSEL2_Q7_COMMAND'],
}
for token, value in replacements.items():
    if s.count(token) != 1:
        raise SystemExit(f'expected exactly one {token}, found {s.count(token)}')
    if not value.strip():
        raise SystemExit(f'empty binding for {token}')
    s = s.replace(token, value)
if 'kind: qualification-handoff\n' not in s:
    raise SystemExit('final handoff kind is not qualification-handoff')
if '__' in s or '<CAMPAIGN_DATABASE>' in s or '<DOMAIN>' in s:
    raise SystemExit('unresolved placeholder remains in final handoff')
dst.write_text(s, encoding='utf-8')
src.unlink()
PY

HANDOFF_SHA=$(sha256sum "$HANDOFF" | awk '{print $1}')
printf 'candidate_content_identity=%s\nqualification_handoff_sha256=%s\n' "$DIGEST" "$HANDOFF_SHA"
```

## 4. Implementation-boundary checks

```bash
grep -Fx 'kind: qualification-handoff' "$HANDOFF"
grep -F "candidate_content_identity: $DIGEST" "$HANDOFF"
! grep -E '__[A-Z0-9_]+__|<CAMPAIGN_DATABASE>|<DOMAIN>' "$HANDOFF"
git diff --exit-code -- . \
  ':(exclude)workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json' \
  ':(exclude)workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md'
git status --porcelain=v1 --untracked-files=all
```

Expected post-bootstrap changes are limited to the generated candidate-identity and exact-handoff coordination files plus declared qualification output directories. No product/test/spec/config/package/release path may change.

Once these checks pass, record `HANDOFF_SHA`, switch to `software-qualification`, and consume only `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md`. Product source mutation remains forbidden.
