# Contributing

## Development setup

The core currently uses only the Python standard library.

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## Testing

Run the standard test command before handing off a change.

## Coding rules

- Keep domain rules free of vendor SDK imports.
- Put external API calls in `src/hungryradar/adapters/`.
- Return typed, structured facts from adapters.
- Preserve source URI and checked time for externally sourced facts.
- Add a test for each product rule before adding an integration.

## Pull Request Process

Keep changes focused, explain the boundary being added, and include tests for new rules.

## Change checklist

- Tests pass.
- `git diff --check` passes.
- New provider behavior is behind a port.
- Architecture docs are updated when a boundary changes.
