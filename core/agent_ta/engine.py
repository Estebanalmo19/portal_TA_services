"""Agent TA: a small, fully local, rule-based FAQ engine.

No LLM, no remote model, no API key — this module only ever returns
predefined strings from ``faqs.py`` (or one of the fixed fallback/guard
messages below). User input is treated purely as data used to *select*
which predefined answer to show; it can never add a new answer, change the
catalog, or alter these rules. See docs/implementation-notes.md for the
scope-guard design rationale and its known limits (this is pattern
matching, not a guarantee against every possible phrasing).
"""

import re
import unicodedata
from dataclasses import dataclass

from . import faqs as faq_data

# --- normalization -----------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def tokens(text: str) -> set[str]:
    return set(normalize(text).split())


_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "en", "y", "o", "que", "es", "son", "para", "por", "con", "se", "mi",
    "tu", "su", "a", "como", "cual", "cuales", "sobre", "me", "puedo",
    "puede", "hacer",
}

_GREETINGS = {
    "hola", "buenas", "buenos", "dias", "tardes", "noches", "hey", "holi",
    "saludos", "gracias",
}


def _significant_tokens(text: str) -> set[str]:
    return tokens(text) - _STOPWORDS


def _content_tokens(text: str) -> set[str]:
    return _significant_tokens(text) - _GREETINGS


# --- scope keywords ------------------------------------------------------

TA_KEYWORDS = _significant_tokens(
    "referido referidos referral referrals vacante vacantes candidato candidatos "
    "reclutador reclutadora recruiter entrevista entrevistas contratado contratacion "
    "postulacion postular etapa etapas talent acquisition ta seleccion cv hoja de vida "
    "hired rejected under review submitted interview recruiter assigned proceso de "
    "seleccion referente"
)

OTHER_DOMAIN_KEYWORDS = {
    "hr": _significant_tokens(
        "nomina vacaciones certificacion laboral beneficios contrato retiro renuncia "
        "hr colombia ticketing solicitud general actualizacion de datos"
    ),
    "security": _significant_tokens(
        "incidente de seguridad acceso credencial camara puerta electroiman locker "
        "ascensor edr visitante activo de seguridad security database hub"
    ),
    "uniform": _significant_tokens(
        "uniforme camisa pantalon calzado accesorio uniform compliance check checklist "
        "de uniforme"
    ),
    "appearance": _significant_tokens(
        "appearance check apariencia presentacion tatuaje revision de apariencia "
        "aprobado requiere revision"
    ),
    "automation_general": _significant_tokens(
        "automation health center hibob heinsohn mailbox tracker restricted companies "
        "screening"
    ),
}

_INJECTION_PATTERNS = [
    re.compile(p)
    for p in [
        r"\bignora\b.*\b(instruccion|instrucciones|regla|reglas)\b",
        r"\bolvida\b.*\b(instruccion|instrucciones|regla|reglas)\b",
        r"\bactua como\b",
        r"\bfinge ser\b",
        r"\beres ahora\b",
        r"\bnuevo rol\b",
        r"\bsystem prompt\b",
        r"\bprompt del sistema\b",
        r"\bsaltate\b",
        r"\bdesactiva\b.*\b(filtro|restriccion|restricciones)\b",
    ]
]


def _is_injection_attempt(normalized: str) -> bool:
    return any(p.search(normalized) for p in _INJECTION_PATTERNS)


@dataclass
class MatchResult:
    faq: dict | None
    score: float


def best_faq_match(normalized: str) -> MatchResult:
    input_tokens = _significant_tokens(normalized)
    best_faq = None
    best_score = 0.0
    for faq in faq_data.FAQS:
        faq_best = 0.0
        for intent in faq["intents"]:
            norm_intent = normalize(intent)
            if norm_intent and norm_intent in normalized:
                faq_best = max(faq_best, 1.0)
                continue
            intent_tokens = _significant_tokens(intent)
            if not intent_tokens:
                continue
            overlap = input_tokens & intent_tokens
            score = len(overlap) / len(intent_tokens)
            faq_best = max(faq_best, score)
        if faq_best > best_score:
            best_score = faq_best
            best_faq = faq
    return MatchResult(best_faq, best_score)


FAQ_MATCH_THRESHOLD = 0.6


def _score_domain_keywords(input_tokens: set[str], keywords: set[str]) -> int:
    return len(input_tokens & keywords)


def answer(message: str) -> dict:
    """Return a dict shaped like:
    ``{"reply": str, "kind": "answer"|"ambiguous"|"unknown_in_scope"|"out_of_scope"|"guarded",
       "faq_id": str|None, "suggested": [str, ...], "support_hint": bool}``
    """
    normalized = normalize(message)
    input_tokens = _significant_tokens(message)

    if not _content_tokens(message):
        return {
            "reply": faq_data.AMBIGUOUS_REPLY,
            "kind": "ambiguous",
            "faq_id": None,
            "suggested": faq_data.SUGGESTED_QUESTIONS,
            "support_hint": False,
        }

    if _is_injection_attempt(normalized):
        return {
            "reply": faq_data.GUARDED_REPLY,
            "kind": "guarded",
            "faq_id": None,
            "suggested": faq_data.SUGGESTED_QUESTIONS,
            "support_hint": False,
        }

    ta_hits = _score_domain_keywords(input_tokens, TA_KEYWORDS)
    other_scores = {
        domain: _score_domain_keywords(input_tokens, kws)
        for domain, kws in OTHER_DOMAIN_KEYWORDS.items()
    }
    best_other_domain = max(other_scores, key=lambda d: other_scores[d]) if other_scores else None
    best_other_score = other_scores.get(best_other_domain, 0) if best_other_domain else 0

    if ta_hits == 0 and best_other_score == 0:
        return {
            "reply": faq_data.OUT_OF_SCOPE_REPLY,
            "kind": "out_of_scope",
            "faq_id": None,
            "suggested": faq_data.SUGGESTED_QUESTIONS,
            "support_hint": False,
        }

    if best_other_score > 0 and best_other_score >= ta_hits:
        # A mention of another domain dominates (or ties) the TA signal: a
        # single incidental "TA"/"referido" word must not make an
        # HR/Security/Uniform/etc. question look valid.
        return {
            "reply": faq_data.OUT_OF_SCOPE_REPLY,
            "kind": "out_of_scope",
            "faq_id": None,
            "suggested": faq_data.SUGGESTED_QUESTIONS,
            "support_hint": False,
        }

    match = best_faq_match(normalized)
    if match.faq and match.score >= FAQ_MATCH_THRESHOLD:
        return {
            "reply": match.faq["answer"],
            "kind": "answer",
            "faq_id": match.faq["id"],
            "suggested": faq_data.SUGGESTED_QUESTIONS,
            "support_hint": bool(match.faq.get("support_hint")),
        }

    if ta_hits <= 1 and len(input_tokens) <= 3:
        return {
            "reply": faq_data.AMBIGUOUS_REPLY,
            "kind": "ambiguous",
            "faq_id": None,
            "suggested": faq_data.SUGGESTED_QUESTIONS,
            "support_hint": False,
        }

    return {
        "reply": faq_data.UNKNOWN_IN_SCOPE_REPLY,
        "kind": "unknown_in_scope",
        "faq_id": None,
        "suggested": faq_data.SUGGESTED_QUESTIONS,
        "support_hint": True,
    }
