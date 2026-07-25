# Prompt Lab Conventions

## Directory Structure

```
prompt-lab/
├── core/               # Engine core (universal logic, zero user data)
├── cli/                # CLI entry points
├── web/                # Web UI (future)
├── tests/              # Test code
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test fixtures
├── docs/               # All documentation
│   ├── 00-positioning/ # Product positioning
│   ├── 01-prd/         # Product requirements
│   ├── 02-spec/        # Technical specs
│   ├── 03-plan/        # Implementation plans
│   ├── 04-test-plan/   # Test plans
│   └── adr/            # Architecture decision records
├── examples/           # Example projects and demos
├── scripts/            # Utility scripts
└── README.md
```

## Naming Conventions

| Type | Location | Pattern |
|------|----------|---------|
| Engine code | `core/` | `snake_case.py` |
| CLI | `cli/` | `snake_case.py` |
| Tests | `tests/unit/` | `test_<module>.py` |
| Docs | `docs/` | `kebab-case` |
| Config | root | `*.yaml` / `*.json` |

## Git Workflow

- `main` is the only development branch
- Feature branches: `feature/<name>`
- Fix branches: `fix/<name>`
