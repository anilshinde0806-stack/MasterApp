# MasterApp Project Structure

MasterApp is being migrated incrementally from a large Django application to a
layered modular architecture. The legacy adapters remain active until each use
case has tests and a stable replacement.

## Active boundaries

```text
config/                 Django composition root (settings, URLs, middleware)
core/                   Legacy Django app: ORM models and web presentation
mobile_api/             DRF/mobile presentation adapter
rbac/                   Django role and menu management app
reports/                Reporting adapter
apps/core/              Framework-independent MOS primitives and runtime
apps/bodyshop/          Body-shop domain module and application commands
apps/claims/            Claims services, repositories, DTOs, and API adapters
erp/                    Database assets and external integration adapters
```

## Dependency direction

```text
presentation -> application/services -> domain contracts
infrastructure -----------------------> domain contracts
config -> all concrete adapters (composition only)
```

- `apps/core/domain` and `apps/core/foundation` must not import Django.
- `apps/bodyshop/domain` must not import `core.models`, DRF, or templates.
- ORM access belongs in repositories or infrastructure adapters.
- `core/` and `mobile_api/` may call application services during migration,
  but application services must not import views.
- New API endpoints belong in the owning module's `api/` package; URL aliases
  may remain in `mobile_api.urls` for backward compatibility.

## Incremental refactor order

1. Keep database models and migrations in `core` until model ownership is
   explicitly migrated with state-preserving Django migrations.
2. Move business calculations out of `core.views` and `mobile_api.views` into
   `apps/<module>/services` with focused tests.
3. Move ORM queries into `apps/<module>/repositories`.
4. Move endpoint functions into `apps/<module>/api` while preserving existing
   URL names and response contracts.
5. Split `core.models` by model module only after all imports use stable public
   exports from `core.models`.

## Rules for new code

- Do not add business logic to `core/views.py` or `mobile_api/views.py`.
- Do not create another generic `utils.py`; place helpers with their module.
- Avoid import-time I/O and `print`; use module-level logging.
- Every migrated use case needs a service test before its legacy code is
  removed.
- Refactors must pass `manage.py check` and the relevant focused test suite.
