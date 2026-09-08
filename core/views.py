from urllib.parse import urlencode

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from core.agent_ta import engine as agent_ta_engine
from core.catalog import catalog_cards
from core.state import json_error, json_ok, parse_json_body, require_post
from mock_data.reference import SOLUTION_BY_SLUG, SOLUTIONS


@ensure_csrf_cookie
def welcome(request):
    next_path = request.GET.get("next", "")
    return render(request, "core/welcome.html", {"next_path": next_path})


@ensure_csrf_cookie
def catalog(request):
    return render(request, "core/catalog.html", {"cards": catalog_cards()})


@ensure_csrf_cookie
def about(request):
    return render(request, "core/about.html")


@ensure_csrf_cookie
def global_search(request):
    query = (request.GET.get("q") or "").strip().lower()
    results = []
    if len(query) >= 2:
        for solution in SOLUTIONS:
            haystack = f"{solution['name']} {solution['description']}".lower()
            if query in haystack:
                results.append(
                    {
                        "kind": "solution",
                        "label": solution["name"],
                        "hint": solution["description"],
                        "url": f"/soluciones/{solution['slug']}/",
                    }
                )
    return json_ok({"query": query, "results": results[:12]})


def _support_prefill_url(solution_slug: str, message: str) -> str:
    solution = SOLUTION_BY_SLUG.get(solution_slug)
    subject = f"Problema con {solution['name']}" if solution else "Problema con una herramienta de TA"
    params = urlencode(
        {
            "sol": solution_slug if solution else "ta",
            "asunto": subject,
            "descripcion": message[:400],
            "origen": "agent_ta",
        }
    )
    return f"/soluciones/support/?{params}"


@require_post
def agent_ta_ask(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return json_error(str(exc))

    message = str(payload.get("message", ""))[:1000]
    if not message.strip():
        return json_error({"message": "Escribe una pregunta para Agent TA."})

    result = agent_ta_engine.answer(message)
    response = {
        "reply": result["reply"],
        "kind": result["kind"],
        "faq_id": result["faq_id"],
        "suggested": result["suggested"],
    }
    if result["support_hint"]:
        response["support_url"] = _support_prefill_url("referral", message)
    return json_ok(response)


def error_404_view(request, exception=None):
    return render(request, "404.html", status=404)


def error_500_view(request):
    return render(request, "500.html", status=500)
