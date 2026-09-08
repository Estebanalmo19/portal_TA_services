"""Shared validation, ID-generation and state-transition helpers used by
every solution's ``services`` module.

These are plain functions operating on dicts — there are no Django models
in this project (see ``docs/implementation-notes.md``). Every solution's
service module builds its own domain rules (statuses, transitions, scoring)
on top of the primitives here, so the rules live in exactly one place and
Python/JavaScript never disagree about a KPI or a transition.
"""

import re
from datetime import datetime

from django.utils import timezone
from django.utils.html import escape as html_escape

_ID_RE_CACHE: dict[str, re.Pattern] = {}


class ValidationError(Exception):
    """Carries a dict of ``{field_name: message}``. ``__all__`` is used for
    errors that are not attached to a single field."""

    def __init__(self, errors: dict):
        self.errors = dict(errors)
        super().__init__(repr(self.errors))


class Validator:
    """Accumulates field errors so a form-like payload can report every
    problem at once instead of failing on the first bad field."""

    def __init__(self):
        self.errors: dict[str, str] = {}
        self.cleaned: dict = {}

    def raise_if_errors(self):
        if self.errors:
            raise ValidationError(self.errors)

    def text(self, payload, field, *, label=None, max_length=2000, min_length=1, required=True, default=""):
        label = label or field
        raw = payload.get(field, default)
        if raw is None:
            raw = ""
        value = str(raw).strip()
        if required and not value:
            self.errors[field] = f"{label}: este campo es obligatorio."
            self.cleaned[field] = ""
            return ""
        if value and len(value) < min_length:
            self.errors[field] = f"{label}: debe tener al menos {min_length} caracteres."
        if len(value) > max_length:
            value = value[:max_length]
        self.cleaned[field] = value
        return value

    def choice(self, payload, field, choices, *, label=None, required=True, default=None):
        label = label or field
        value = payload.get(field, default)
        if value not in choices:
            if required:
                self.errors[field] = f"{label}: selecciona una opción válida."
            self.cleaned[field] = default
            return default
        self.cleaned[field] = value
        return value

    def optional_choice(self, payload, field, choices, *, label=None, default=None):
        return self.choice(payload, field, choices, label=label, required=False, default=default)

    def id_ref(self, payload, field, valid_ids, *, label=None, required=True):
        label = label or field
        value = payload.get(field)
        if not value:
            if required:
                self.errors[field] = f"{label}: este campo es obligatorio."
            return None
        if valid_ids is not None and value not in valid_ids:
            self.errors[field] = f"{label}: referencia desconocida."
            return None
        self.cleaned[field] = value
        return value


def sanitize_text(value: str) -> str:
    """Escape user-authored free text before it is echoed back in a server
    response or CSV cell. The frontend also renders via ``textContent``
    rather than ``innerHTML``; this is defense in depth, not the only
    layer."""
    return html_escape(str(value or "")).strip()


def next_id(prefix: str, existing_ids, *, width: int = 4) -> str:
    """Compute the next free ``PREFIX-0001``-style id given the ids the
    browser currently knows about. Deterministic and collision-free as long
    as the browser always reports its current tab-local id list back."""
    pattern = _ID_RE_CACHE.setdefault(prefix, re.compile(rf"^{re.escape(prefix)}-(\d+)$"))
    max_n = 0
    for existing in existing_ids or []:
        match = pattern.match(str(existing))
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"{prefix}-{max_n + 1:0{width}d}"

def now_iso() -> str:
    return timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def history_entry(event_type: str, detail: str, *, actor: str = "Colaborador Demo") -> dict:
    return {
        "type": event_type,
        "detail": sanitize_text(detail),
        "actor": sanitize_text(actor),
        "at": now_iso(),
    }


class TransitionGraph:
    """A small finite-state-machine: ``{status: {allowed_next_statuses}}``.

    Shared by Python (source of truth, used at save time) and mirrored in
    each solution's JS module for optimistic UI (disabling buttons that
    would be rejected anyway) — the JS copy is a UX nicety, never the
    authority; see docs/implementation-notes.md.
    """

    def __init__(self, edges: dict[str, set[str]], *, terminal: set[str] | None = None):
        self.edges = edges
        self.terminal = terminal or set()

    @property
    def statuses(self):
        return list(self.edges.keys())

    def allowed_next(self, current: str) -> set[str]:
        return self.edges.get(current, set())

    def can_transition(self, current: str, target: str) -> bool:
        if current == target:
            return False
        return target in self.allowed_next(current)

    def validate(self, current: str, target: str):
        if current not in self.edges:
            raise ValidationError({"status": "Estado actual desconocido."})
        if target not in self.edges:
            raise ValidationError({"status": "Estado destino desconocido."})
        if not self.can_transition(current, target):
            raise ValidationError(
                {"status": f"No se permite pasar de «{current}» a «{target}»."}
            )


def csv_cell(value) -> str:
    """Neutralize spreadsheet-formula injection (CSV is often opened in
    Excel/Sheets): a leading =,+,-,@ or tab/CR turns a cell into a formula
    in some spreadsheet apps unless neutralized."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text
