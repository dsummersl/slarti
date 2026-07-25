# slarti

[![Slartibartfast](https://static.wikia.nocookie.net/hitchhikers/images/f/f9/Slartibartfast_comics.png/revision/latest?cb=20230703161559)](https://en.wikipedia.org/wiki/Slartibartfast)
Slartibartfas: the curmudgeonly architect of Norway's fjords from *The Hitchhiker's Guide to the Galaxy*. The namesake of this tool.

A coordination CLI for validated architecture documentation.

Slarti provides consistency between three tools:

- [LikeC4](https://likec4.dev): a high level system architecture tool.
- [LinkML](https://linkml.io): A data modeling language.
- [pyshacl](https://github.com/rdflib/pyshacl): A [SHACL](https://www.w3.org/TR/shacl/) graph graph validator (which LinkML can generate).

The table below is the whole division of labour; the sections after it show the seams.


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

### Each tool, used for what it is good for

The seams are what `slarti` adds. They are not what makes each tool worth having.
Every one of these three is useful on its own, on the same sources, with no
`slarti` involved — and `slarti` neither wraps nor hides any of it.

#### LinkML — one definition, projected into every shape that needs it

This is the thing LinkML is best at, and the reason the schema is worth writing:
you define an entity once and *export* it into whatever shape each consumer
needs. The generators run straight against `model/schema/*.yaml`:

```bash
gen-pydantic    model/schema/slarti.yaml > slarti/domain.py     # Python interfaces
gen-typescript  model/schema/slarti.yaml > web/src/domain.ts    # TS types + enums
gen-json-schema model/schema/slarti.yaml > build/slarti.schema.json
gen-shacl       model/schema/slarti.yaml > build/slarti.shapes.ttl
gen-sqlddl      model/schema/slarti.yaml > build/slarti.sql
gen-erdiagram   model/schema/slarti.yaml > docs/diagrams/entities.mmd
```

One slot, four target languages. This entity —

```yaml
# model/schema/slarti.yaml
Finding:
  attributes:
    id:
      description: A stable check ID such as OWN-1; retired IDs are never reused.
      required: true
    severity:
      range: Severity        # an enum: error | warning
      required: true
    line:
      range: integer         # optional: not every finding can be located
```

— becomes a Python interface, a TypeScript type and a JSON Schema without being
written three times:

```python
# slarti/domain.py — gen-pydantic
class Finding(ConfiguredBaseModel):
  id: str = Field(default=...)
  severity: Severity = Field(default=...)
  line: Optional[int] = Field(default=None)
```

```typescript
// gen-typescript
export enum Severity { error = "error", warning = "warning" };
export interface Finding { id: string, severity: Severity, line?: number }
```

```json
// gen-json-schema — feed it to ajv, or to json-schema-to-zod for a zod schema
{ "properties": { "severity": { "$ref": "#/$defs/Severity" },
                "line": { "type": ["integer", "null"] } },
"required": ["id", "severity", "file", "subject", "message", "remedy"] }
```

**`slarti` eats its own here.** `slarti/domain.py` above is not an illustration:
it is the module the implementation imports. `findings.py`, `registry.py`,
`models.py`, `inject.py` and `env.py` declare no entity of their own — they add
behaviour around the generated classes, and `slarti check --json` emits a
generated `Report`, so the JSON an agent parses is the shape the schema declares
by construction. Regenerate with `make domain`; a stale `slarti/domain.py` fails
the test suite the same way a stale document fails `slarti docs --check`
(ADR-0003).

#### LikeC4 — a documentation tool, on its own

LikeC4 does not need `slarti` to be useful. Point it at `model/arch/` and it is a
complete architecture-documentation workflow:

```bash
likec4 start model/arch                    # live browser, every view, hot reload
likec4 codegen mermaid model/arch -o out/  # Mermaid per view, for any Markdown
likec4 export png     model/arch -o out/   # images for a wiki or a slide
likec4 build          model/arch -o site/  # a static site of the whole model
likec4 export json    model/arch -o m.json # the model, for anything else
```

Those are the same commands `slarti docs` shells out to, at the version you
pinned. If you drop `slarti` tomorrow, `model/arch/*.c4` and your diagrams keep
working exactly as they do today; what you lose is the check that the diagram in
the document is still the one the model produces.

#### pyshacl — a validator, on its own

Likewise `model/shapes/*.ttl` is ordinary SHACL over ordinary RDF, and pyshacl
validates it with no coordination layer in sight:

```bash
pyshacl -s model/shapes/invariants.ttl -df turtle data.ttl    # conforms?
linkml-convert -s model/schema/todo.yaml -C Task -t ttl task.yaml > data.ttl
```

Run it in a data pipeline, a pre-commit hook, or a service — the shapes are yours
and portable. What `slarti check` adds is the negative half: every rule declares a
fixture that *must* fail and *must* name that rule's shape, so a shape that
quietly stops firing becomes a finding instead of a green build.

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
slarti report        # enforced rules, unenforced rules, orphaned shapes, check IDs
slarti report --json # the same, fully detailed, for an agent
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
make domain  # regenerate slarti/domain.py from model/schema/slarti.yaml
make ci      # tests, lint, types, complexity, duplication, dead code
```

## ADRs

Architecture Decision Records live in `docs/adr/`.
