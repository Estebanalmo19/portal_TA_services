"""Shared helpers for the "operation" endpoints every solution exposes.

Design contract (see docs/implementation-notes.md for the full write-up):

1. The browser is the source of truth for *which tab-local records exist*;
   Django never stores business records between requests.
2. Every write goes through a POST endpoint that receives a JSON body with
   the operation's payload (and, when the operation needs to compute a new
   ID or a derived aggregate, the minimal slice of demo state required —
   e.g. the list of existing IDs, not the whole dataset).
3. Django validates, applies the (whitelisted, hand-written) domain logic in
   ``solutions.services.*``, and returns either
   ``{"ok": true, "result": {...}}`` or
   ``{"ok": false, "errors": {"field": "message", ...}}`` (HTTP 400).
4. The payload the browser sends is bounded in size/depth before it is even
   looked at, because it is attacker-controlled input, not a trusted
   session — even though the only thing at stake in this demo is the
   simulation itself, not a real security boundary.
"""

import json

from django.conf import settings
from django.http import HttpResponseNotAllowed, JsonResponse


class PayloadTooComplex(ValueError):
    pass


def _check_depth(value, max_depth, current=0):
    if current > max_depth:
        raise PayloadTooComplex("El estado enviado supera la profundidad permitida.")
    if isinstance(value, dict):
        for v in value.values():
            _check_depth(v, max_depth, current + 1)
    elif isinstance(value, list):
        for v in value:
            _check_depth(v, max_depth, current + 1)


def parse_json_body(request, *, max_bytes=None, max_depth=None):
    """Parse and bound-check a JSON request body.

    Raises ``ValueError`` (including :class:`PayloadTooComplex`) on any
    problem; callers should turn that into a 400 JSON error response.
    """
    max_bytes = settings.DEMO_STATE_MAX_BYTES if max_bytes is None else max_bytes
    max_depth = settings.DEMO_STATE_MAX_DEPTH if max_depth is None else max_depth

    body = request.body
    if len(body) > max_bytes:
        raise ValueError("El estado enviado supera el tamaño permitido.")
    if not body:
        return {}
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("El cuerpo de la solicitud no es JSON válido.") from exc
    if not isinstance(data, dict):
        raise ValueError("El cuerpo de la solicitud debe ser un objeto JSON.")
    _check_depth(data, max_depth)
    return data


def json_error(errors, status=400):
    if isinstance(errors, str):
        errors = {"__all__": errors}
    return JsonResponse({"ok": False, "errors": errors}, status=status)


def json_ok(result, status=200):
    return JsonResponse({"ok": True, "result": result}, status=status)


def require_post(view):
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return view(request, *args, **kwargs)

    return wrapped


def operation_endpoint(handler):
    """Decorator for a POST-only JSON operation endpoint.

    ``handler(request, payload) -> dict`` should return the plain result
    dict on success, or raise :class:`solutions.services.common.ValidationError`
    on invalid input (see that module).
    """
    from solutions.services.common import ValidationError

    @require_post
    def wrapped(request, *args, **kwargs):
        try:
            payload = parse_json_body(request)
        except ValueError as exc:
            return json_error(str(exc))
        try:
            result = handler(request, payload, *args, **kwargs)
        except ValidationError as exc:
            return json_error(exc.errors)
        return json_ok(result)

    return wrapped
