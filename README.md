# slarti

A coordination CLI for validated architecture documentation.

Architecture documents drift, and the drift is invisible: a stale diagram looks
exactly like a fresh one, and an unenforced rule in prose reads exactly like an
enforced one.

[LikeC4](https://likec4.dev) validates structure and generates diagrams.
[LinkML](https://linkml.io) validates entities and generates schemas and
projections. Neither can see the other, and neither can see the prose document
that claims what they enforce. `slarti` coordinates them — it does not wrap,
hide or replace any part of either. It owns exactly the joins nobody else holds:

| Join | What goes wrong without it |
|------|----------------------------|
| LikeC4 ↔ LinkML | An entity exists that no container owns, or a container claims an entity that isn't in the schema. |
| Document ↔ rules | The constraints table says a rule is enforced by a shape that was deleted; or a shape exists that no rule references. |
| Document ↔ models | A diagram in the document no longer matches the model it came from. |

Everything else — parsing, validating, rendering, generating — is delegated to
LikeC4, LinkML and pyshacl as subprocesses, at the versions *you* pinned.

## The three tools, and where they meet

`slarti` delegates every piece of real work to one of three tools. Each answers a
different kind of question, and none of them can answer another's. The table below
is the whole division of labour; the sections after it show the seams.

| Tool | Layer | Owns | Cannot say |
|------|-------|------|------------|
| LikeC4 | 1 — structure | Components, containment, allowed relationships, diagrams | Anything about a field or an instance |
| LinkML | 2 — schema | Entities, slots, types, cardinality, generated projections | Where an entity is deployed; any cross-instance invariant |
| pyshacl | 3 — instance | Conformance of real data against SHACL shapes | Anything about code that never ran |

### LikeC4 — structure

**Responsible for:** parsing `model/arch/*.c4`, rejecting dangling relations and
invalid views, generating Mermaid diagrams, and exporting the whole model as JSON.

**`slarti` uses it for:** every layer-1 constraint (`likec4_element`,
`likec4_relation`, `likec4_absent_relation`), the container half of the ownership
seam, and the diagrams injected into `docs/architecture.md`.

```c4
// model/arch/todo.c4
web = container 'Web UI' {
  metadata {
    owns 'Task, TaskList'        // ← the seam: names LinkML classes
  }
}
```

### LinkML — schema

**Responsible for:** validating `model/schema/*.yaml`, resolving it as a
`SchemaView`, and generating SHACL, ER diagrams and implementation projections
(`gen-pydantic`, `gen-typescript`, `gen-sqlddl`, `gen-json-schema`).

**`slarti` uses it for:** every layer-2 constraint (`linkml_class`, `linkml_slot`),
the entity half of the ownership seam, and converting YAML fixtures to RDF.

```yaml
# model/schema/todo.yaml
classes:
  Task:
    annotations:
      owner: todo.web            # ← the seam: names a LikeC4 container
    attributes:
      list:
        required: true
```

### pyshacl — instances

**Responsible for:** running a shapes graph against a data graph and naming every
violated shape.

**`slarti` uses it for:** every layer-3 constraint (`shacl_shape`). Each such rule
declares one negative fixture; `slarti check` asserts the fixture *fails* and that
the report *names that rule's shape*, so a shape that quietly stops firing becomes a
finding instead of a green build.

```turtle
# model/shapes/invariants.ttl
todo:SubtaskSharesListWithParent a sh:NodeShape ;
  sh:targetClass todo:Task ; ... .
```

### How the seams match up — one example

One rule, `D8 — a subtask belongs to the same list as its parent`, touches all three:

```yaml
# model/constraints.yaml
- id: D8
  statement: A subtask belongs to the same list as its parent.
  enforced_by:
    layer: 3
    kind: shacl_shape
    ref: "todo:SubtaskSharesListWithParent"
    fixture: model/data/invalid/D8.yaml
    fixture_class: Task
```

Running `slarti check` walks the seams in order:

1. **LikeC4 ↔ LinkML.** `todo.web` claims `Task`; `Task` names `todo.web` as its
   owner. Delete either side and you get `OWN-3` or `OWN-4` — neither tool alone
   would have noticed.
2. **Registry ↔ models.** `todo:SubtaskSharesListWithParent` must exist in the
   merged shapes graph, or `D8` is a `REG-1` finding: the document would otherwise
   still claim the rule is enforced.
3. **Registry ↔ data.** `model/data/invalid/D8.yaml` is converted by LinkML and run
   through pyshacl. It must fail (`REG-6`) *and* the report must name
   `todo:SubtaskSharesListWithParent` (`REG-7`).
4. **Document ↔ everything.** `slarti docs --check` regenerates the constraints
   table and fails if the committed `docs/architecture.md` no longer matches
   (`DOC-1`).

Each tool decided only what it can see. `slarti` decided nothing about tasks, lists
or diagrams — only that the three answers still refer to the same thing.

## Install

```bash
uv tool install slarti     # the CLI
npm install likec4         # your pinned LikeC4; slarti uses npx --no-install
pip install linkml pyshacl # your pinned LinkML and pyshacl
```

## Use

```bash
slarti init          # scaffold the layout; never overwrites a file
slarti doctor        # probe every delegated tool, version and location
slarti check         # delegated validations, then every seam check (the CI command)
slarti check --json  # the same, as structured findings for an agent
slarti docs          # regenerate diagrams and tables into docs/architecture.md
slarti docs --check  # the drift gate: fail if the committed tree is stale
slarti dangling      # enforced rules, unenforced rules, orphaned shapes
slarti explain OWN-3 # what a check or constraint ID means, and its remedy
```

Exit codes: `0` clean · `1` findings · `2` environment or usage error.

## Layout

```
slarti.toml            paths only; no settings mirrored from other tools
model/
  arch/*.c4            user-authored — LikeC4
  schema/*.yaml        user-authored — LinkML
  shapes/*.ttl         user-authored — hand-written SHACL
  constraints.yaml     user-authored — the rule registry
  data/valid/*         fixtures that must pass
  data/invalid/*       one fixture per rule; each must fail, naming its rule
docs/
  architecture.md      user-authored prose + generated regions
  diagrams/            GENERATED — never hand-edited
```

## The constraint registry

`model/constraints.yaml` is the join table between prose and enforcement:

```yaml
constraints:
  - id: D2
    statement: A task belongs to exactly one list.
    enforced_by:
      layer: 2
      kind: linkml_slot
      ref: "Task.list"

  - id: U1
    statement: The API checks membership before every list access.
    enforced_by: none
    reason: Layer 1 can assert the relationship exists, not that every code path uses it.
```

Every rule points at an enforcer `slarti` resolves against the real models, or
says `enforced_by: none` with a reason. Unenforced is honest; unstated is not.
Enforcer kinds: `shacl_shape`, `linkml_slot`, `linkml_class`, `likec4_relation`,
`likec4_absent_relation`, `likec4_element`, `ownership`, `external`.

## Checks

- `OWN-1..5` — the ownership seam between LinkML classes and LikeC4 containers,
  checked in both directions.
- `REG-1..7` — the registry seam: dangling enforcers, orphaned shapes, missing
  reasons, duplicate IDs, and per-rule negative fixtures that must actually fire.
- `DOC-1..4` — the document seam: stale regions, hand-edited diagrams, broken
  markers, and rules with no row in the tables.
- `ENV-1` — a delegated tool missing or outside its supported version range.

Supported ranges: LikeC4 `>=1.59,<2`, LinkML `>=1.11,<2`, Node `>=20`,
Python `>=3.11,<4`. Outside the range `slarti` refuses to run rather than
producing possibly-wrong output.

## Dogfooding

`slarti`'s own architecture document, [docs/architecture.md](docs/architecture.md),
is generated by `slarti` from [model/](model/), and CI runs `slarti check` and
`slarti docs --check` against this repository.

## Dev setup

```bash
make setup   # uv venv + sync
npm ci       # the pinned LikeC4
make ci      # tests, lint, types, complexity, duplication, dead code
```

## ADRs

Architecture Decision Records live in `docs/adr/`.
