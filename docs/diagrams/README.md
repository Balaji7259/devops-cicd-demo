# Diagrams

Published copies of the architecture diagrams. These are the versions referenced
by the [README](../../README.md) and by [ARCHITECTURE.md](../ARCHITECTURE.md), so
they render directly on GitHub.

| File | What it shows |
|---|---|
| [architecture-overview.png](architecture-overview.png) | The whole system after Phase 4 — runner, registry, instance, and what is absent (no SSH key, no port 22) |
| [iam-model.png](iam-model.png) | Both identities, what each may do, and why neither can delete anything |
| [ci-vs-cd.png](ci-vs-cd.png) | Integration versus deployment, and the point where a failed check stops a release |
| [deploy-gates.png](deploy-gates.png) | The four gates and what happens when each one fails |
| [deploy-via-ssm.png](deploy-via-ssm.png) | How a deploy reaches the server without a connection into it |
| [rollback-flow.png](rollback-flow.png) | The health check, the restore path, and why a rollback still fails the run |

## Regenerating

```bash
python build/gen_arch_diagrams.py   # architecture-overview.png, iam-model.png
python build/gen_diagrams.py        # the rest, into build/diagrams/
```

The two generators are kept because a diagram that cannot be regenerated becomes
wrong the first time the system changes, and nobody notices. The earlier build-log
PDF still contains an SSH-based overview for exactly that reason — it was correct
when it was drawn, and it is kept as a historical record rather than edited.

After regenerating, copy the updated files from `build/diagrams/` into this
folder so the published copies stay current.

## A note on the naming

Files are named by the question they answer (`deploy-via-ssm.png`) rather than by
an index (`d8.png`). Links outlive memory: a URL ending in `d8.png` tells a
reader nothing, and renaming it later breaks every reference.
