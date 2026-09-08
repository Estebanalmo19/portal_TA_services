"""
Centralized, deterministic mock dataset for the ARRISE Solutions Portal demo.

Everything under this package is generated in-memory from a fixed seed and a
frozen "reference date" (see ``mock_data.clock``). Nothing here reads or
writes a database or the filesystem at request time: Django views import
these modules, get plain Python data structures back, and serialize the
parts they need (never the whole graph) into templates or JSON responses.

Contract notes for whoever extends this package:

- Every generator function must be pure given (seed, reference_date): same
  inputs, same output, every process/run. Views must never mutate the
  structures returned here in place; treat them as read-only snapshots and
  copy before modifying (see ``core.state.deep_copy``).
- ``STATE_VERSION`` is the version of the *shape* of the bootstrap payload
  sent to the browser (see ``core/static state contract`` in
  ``docs/implementation-notes.md``). Bump it whenever a field is renamed,
  removed, or a new required field is added, so the frontend can detect and
  discard stale ``sessionStorage`` snapshots instead of crashing on them.
"""

STATE_VERSION = 1
