# Stage 04 — Application  (conditional)

**Goal:** a product, not a library feature: accounts, storage, collaboration and a UI. It
likely lives in its own repository and is versioned on its own.

**Epics (each closer to a project than an epic):**

| Epic | One line | Needs |
|------|----------|-------|
| 4.1 | Hosted render API: tenants, authentication, quotas, storage | 3.2, 3.7 |
| 4.2 | Authoring app: edit a note with every medium previewed side by side | 4.1, 2.5 |
| 4.3 | Review and approval: states, versions and an audit trail, on 1.6 and 2.7 | 4.2 |
| 4.4 | Integrations: data sources and distribution targets | 4.1 |
| 4.5 | Commercial model: pricing, licensing, open core or hosted | 4.1 |

**Gate to start:** at least one team outside the owner uses the Stage 03 API weekly and asks
for something only a hosted service can give.

**Risk:** starting early. An app pulls the roadmap towards UI and accounts and away from the
render quality and research apparatus that set octavo apart.
