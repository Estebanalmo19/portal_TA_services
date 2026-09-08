"""Agent TA's answer bank.

Every entry is predefined content — the engine in ``engine.py`` never
generates free text; it only ever picks one of these answers (or a fixed
fallback/guard message). ``intents`` are the phrases/keywords used to match
a user message to an entry (see ``engine.best_faq_match``); write several
short variants per entry to cover the "variantes lingüísticas" requirement
instead of relying on one exact phrasing.

Every fabricated policy/guide referenced from an answer is explicitly
labelled "Guía de demostración" so nobody mistakes it for a real ARRISE
procedure.
"""

FAQS = [
    {
        "id": "faq-referral-como-registrar",
        "question": "¿Cómo registro un referido?",
        "intents": [
            "como registro un referido",
            "como creo un referido",
            "como envio un referido",
            "registrar un referido",
            "nuevo referido",
            "quiero referir a alguien",
            "como postulo a un candidato",
            "referir candidato",
        ],
        "answer": (
            "Para registrar un referido entra a Referral Portal desde el catálogo y usa "
            "«Nuevo referido». Completa candidato, vacante, país, tu relación con el "
            "candidato y adjunta el CV simulado. Al enviarlo se genera un ID y el "
            "referido queda en estado «Enviado» (Submitted)."
        ),
    },
    {
        "id": "faq-referral-etapas",
        "question": "¿Qué significan las etapas de un referido?",
        "intents": [
            "que significan las etapas",
            "etapas del referido",
            "estados del referido",
            "que es under review",
            "que significa en revision",
            "que es recruiter assigned",
            "que significa reclutador asignado",
            "que es interview",
            "que significa entrevista",
            "que es hired",
            "que significa contratado",
            "que es rejected",
            "que significa rechazado",
        ],
        "answer": (
            "Un referido pasa por: Enviado (Submitted) → En revisión (Under review) → "
            "Reclutador asignado (Recruiter assigned) → Entrevista (Interview) → y "
            "finalmente Contratado (Hired) o Rechazado (Rejected). «En revisión» "
            "significa que Talent Acquisition está validando que el perfil aplique a "
            "la vacante antes de asignar reclutador."
        ),
    },
    {
        "id": "faq-referral-consultar-estado",
        "question": "¿Cómo consulto el estado de un referido?",
        "intents": [
            "como consulto el estado de un referido",
            "donde veo el estado de mi referido",
            "como veo en que va mi referido",
            "estado de mi referido",
            "seguimiento de referido",
            "donde reviso mis referidos",
        ],
        "answer": (
            "En Referral Portal abre la pestaña de tus referidos, busca por nombre del "
            "candidato o ID, y entra al detalle: ahí ves la etapa actual, el historial "
            "completo (timeline) y las notas del reclutador asignado."
        ),
    },
    {
        "id": "faq-referral-notificacion",
        "question": "¿El referente recibe alguna notificación de cambios?",
        "intents": [
            "el referente recibe notificacion",
            "se notifica al referente",
            "aviso al referente",
            "notificacion de cambio de etapa",
        ],
        "answer": (
            "Sí: cuando cambia la etapa de un referido, Referral Portal simula una "
            "notificación interna al referente en el centro de notificaciones del "
            "portal (esta demo no envía correos reales)."
        ),
    },
    {
        "id": "faq-referral-vacante-no-existe",
        "question": "¿Puedo referir a alguien si no encuentro la vacante exacta?",
        "intents": [
            "no encuentro la vacante",
            "la vacante no esta en la lista",
            "que hago si no aparece la vacante",
        ],
        "answer": (
            "Guía de demostración: si la vacante no aparece en el listado, registra el "
            "referido con la vacante más cercana y déjalo indicado en las notas; un "
            "reclutador la reasignará durante la revisión."
        ),
    },
    {
        "id": "faq-referral-rechazado-reintentar",
        "question": "¿Puedo volver a referir a alguien que fue rechazado?",
        "intents": [
            "puedo volver a referir a alguien rechazado",
            "referido rechazado puedo reintentar",
            "candidato rechazado nueva vacante",
        ],
        "answer": (
            "Sí. Un referido en estado «Rechazado» para una vacante no bloquea que lo "
            "vuelvas a referir para una vacante distinta; regístralo como un nuevo "
            "referido indicando la nueva vacante."
        ),
    },
    {
        "id": "faq-ta-navegacion-catalogo",
        "question": "¿Cómo navego entre las soluciones del portal?",
        "intents": [
            "como navego entre soluciones",
            "donde esta el catalogo",
            "como vuelvo al catalogo",
            "donde veo todas las soluciones",
        ],
        "answer": (
            "Usa el logo o «Catálogo» en la barra lateral para volver a la vista de las "
            "siete soluciones. Desde ahí puedes abrir cualquiera, filtrar por área o "
            "estado, y usar la búsqueda global de la parte superior."
        ),
    },
    {
        "id": "faq-ta-busqueda-global",
        "question": "¿Cómo funciona la búsqueda global?",
        "intents": [
            "como funciona la busqueda global",
            "como busco algo en el portal",
            "donde busco un referido o ticket",
        ],
        "answer": (
            "La búsqueda global (icono de lupa en la barra superior) busca por nombre, "
            "ID o palabra clave dentro de los registros de la solución en la que estás, "
            "y en el catálogo busca por nombre de solución."
        ),
    },
    {
        "id": "faq-ta-dashboard",
        "question": "¿Qué muestra el dashboard ejecutivo?",
        "intents": [
            "que muestra el dashboard",
            "para que sirve el dashboard ejecutivo",
            "que es el dashboard",
        ],
        "answer": (
            "El dashboard ejecutivo resume adopción, uso, éxito, horas ahorradas y "
            "alertas de las siete soluciones. Solo el perfil Manager tiene acceso "
            "completo en esta demo; los demás perfiles ven un recorrido limitado."
        ),
    },
    {
        "id": "faq-ta-perfil",
        "question": "¿Qué diferencia hay entre los perfiles Manager, Solution Owner y Analyst?",
        "intents": [
            "diferencia entre perfiles",
            "que hace un manager",
            "que hace un solution owner",
            "que hace un analyst",
            "que perfil debo elegir",
        ],
        "answer": (
            "Manager tiene el recorrido completo y el dashboard ejecutivo. Solution "
            "Owner gestiona asignación, estados y analítica de sus soluciones. Analyst "
            "usa el día a día operativo: crear, consultar y dar seguimiento a "
            "registros. Este selector es solo una simulación de rol, no un control de "
            "acceso real (ver About)."
        ),
    },
    {
        "id": "faq-ta-herramienta-falla",
        "question": "¿Qué hago si falla una herramienta de TA?",
        "intents": [
            "que hago si falla una herramienta de ta",
            "una herramienta de ta no funciona",
            "el referral portal no carga",
            "el portal de referidos esta caido",
            "error en referral portal",
            "no puedo enviar un referido",
        ],
        "answer": (
            "Puedo ayudarte a abrir un ticket en Solutions Support con la herramienta "
            "de Talent Acquisition y un resumen ya precargados; tú revisas los datos y "
            "lo envías."
        ),
        "support_hint": True,
    },
    {
        "id": "faq-ta-automation-falla",
        "question": "¿Qué hago si una automatización de recruiters falla?",
        "intents": [
            "la automatizacion de recruiters fallo",
            "fallo la asignacion automatica de recruiters",
            "error en automation health center de ta",
        ],
        "answer": (
            "Revisa el detalle del fallo en Automation Health Center: ahí puedes ver el "
            "error, reintentar la ejecución y, si continúa fallando, abrir un ticket en "
            "Solutions Support desde el mismo detalle."
        ),
        "support_hint": True,
    },
    {
        "id": "faq-ta-tiempo-respuesta",
        "question": "¿Cuánto tarda Talent Acquisition en revisar un referido?",
        "intents": [
            "cuanto tarda ta en revisar un referido",
            "tiempo de respuesta de un referido",
            "cuanto demora la revision",
        ],
        "answer": (
            "Guía de demostración: en este MVP no hay un SLA real de Talent "
            "Acquisition; el dashboard de Referral Portal muestra tiempos de proceso "
            "de ejemplo por etapa, solo para fines de la demo."
        ),
    },
    {
        "id": "faq-ta-datos-personales",
        "question": "¿Debo compartir información personal real del candidato?",
        "intents": [
            "debo compartir informacion personal real",
            "puedo usar datos reales del candidato",
            "informacion sensible del candidato",
        ],
        "answer": (
            "No. Este portal es una demo: usa siempre datos ficticios de ejemplo, nunca "
            "información personal real de candidatos ni colaboradores."
        ),
    },
    {
        "id": "faq-ta-quien-es-agent-ta",
        "question": "¿Qué puede hacer Agent TA?",
        "intents": [
            "que puede hacer agent ta",
            "que eres",
            "quien eres",
            "para que sirves",
            "que sabes hacer",
        ],
        "answer": (
            "Soy un asistente local de demostración limitado a Talent Acquisition: "
            "referidos, sus etapas, navegación del portal y orientación operativa de "
            "TA. Mis respuestas son predefinidas (Demo · Respuestas simuladas), no "
            "genero texto libre ni me conecto a un modelo externo."
        ),
    },
    {
        "id": "faq-ta-conversacion",
        "question": "¿Se guarda mi conversación con Agent TA?",
        "intents": [
            "se guarda mi conversacion",
            "el chat se borra al recargar",
            "el chat persiste al navegar",
        ],
        "answer": (
            "Tu conversación se conserva en esta pestaña mientras navegas o recargas el "
            "portal. Usa «Nueva conversación» para empezar de cero, o «Restablecer "
            "demo» para borrar todo el estado de la sesión."
        ),
    },
    {
        "id": "faq-ta-conversion-etapa",
        "question": "¿Dónde veo la conversión por etapa de los referidos?",
        "intents": [
            "conversion por etapa",
            "tasa de conversion de referidos",
            "cuantos referidos llegan a contratado",
        ],
        "answer": (
            "En Referral Portal, la pestaña de analítica muestra la conversión por "
            "etapa, la distribución por país y las vacantes más referidas."
        ),
    },
    {
        "id": "faq-ta-vacante-mas-referida",
        "question": "¿Cómo sé qué vacante recibe más referidos?",
        "intents": [
            "que vacante recibe mas referidos",
            "vacantes mas referidas",
            "ranking de vacantes referidas",
        ],
        "answer": (
            "El panel de analítica de Referral Portal incluye un ranking de vacantes "
            "más referidas dentro del periodo seleccionado."
        ),
    },
    {
        "id": "faq-ta-reportar-problema-general",
        "question": "¿Cómo reporto un problema del portal?",
        "intents": [
            "como reporto un problema del portal",
            "boton de reportar un problema",
            "donde reporto un error",
        ],
        "answer": (
            "Cada solución tiene un botón «Reportar un problema» que abre Solutions "
            "Support con esa herramienta ya preseleccionada; revisa el formulario y "
            "envíalo tú mismo."
        ),
        "support_hint": True,
    },
    {
        "id": "faq-ta-restablecer-demo",
        "question": "¿Qué hace «Restablecer demo»?",
        "intents": [
            "que hace restablecer demo",
            "como reinicio la demo",
            "como borro los datos de prueba",
        ],
        "answer": (
            "«Restablecer demo» (en tu perfil) borra registros, comentarios, "
            "notificaciones y conversaciones de esta pestaña, y vuelve a cargar los "
            "datos de ejemplo iniciales. Conserva tu tema visual y el perfil elegido."
        ),
    },
    {
        "id": "faq-ta-modo-oscuro",
        "question": "¿Cómo cambio a modo oscuro?",
        "intents": [
            "como cambio a modo oscuro",
            "donde esta el tema oscuro",
            "activar modo oscuro",
        ],
        "answer": (
            "El interruptor de tema claro/oscuro está en la barra superior, junto al "
            "perfil. Tu preferencia se guarda en este navegador."
        ),
    },
    {
        "id": "faq-ta-hired-siguiente-paso",
        "question": "¿Qué pasa después de que un referido queda Contratado?",
        "intents": [
            "que pasa despues de hired",
            "que sigue despues de contratado",
            "referido contratado siguiente paso",
        ],
        "answer": (
            "Guía de demostración: cuando un referido llega a «Contratado» (Hired) "
            "queda marcado como cierre exitoso del proceso; no dispara ninguna acción "
            "real de nómina ni de sistemas de HR en esta demo."
        ),
    },
    {
        "id": "faq-ta-quien-asigna-reclutador",
        "question": "¿Quién asigna al reclutador de un referido?",
        "intents": [
            "quien asigna al reclutador",
            "como se asigna el reclutador",
        ],
        "answer": (
            "En esta demo, la asignación de reclutador se simula manualmente desde el "
            "detalle del referido al pasar a la etapa «Reclutador asignado»."
        ),
    },
    {
        "id": "faq-ta-fuera-de-alcance-hr-security",
        "question": "¿Agent TA responde dudas de HR o Security?",
        "intents": [
            "agent ta responde dudas de hr",
            "agent ta responde dudas de security",
            "me ayudas con nomina",
            "me ayudas con un incidente de seguridad",
        ],
        "answer": (
            "Puedo enlazarte a HR Colombia Ticketing o a Security Database Hub, pero no "
            "respondo consultas de esos ámbitos: solo cubro Talent Acquisition."
        ),
    },
]

FAQ_BY_ID = {f["id"]: f for f in FAQS}

SUGGESTED_QUESTIONS = [
    "¿Cómo registro un referido?",
    "¿Qué significa Under review?",
    "¿Cómo consulto el estado de un referido?",
    "¿Qué hago si falla una herramienta de TA?",
]

WELCOME_MESSAGE = (
    "Hola, soy Agent TA. Puedo ayudarte con procesos de selección, referidos y uso de "
    "las herramientas de Talent Acquisition. ¿Qué necesitas consultar?"
)

OUT_OF_SCOPE_REPLY = "Puedo ayudarte únicamente con Talent Acquisition"

AMBIGUOUS_REPLY = (
    "¿Podrías darme un poco más de detalle? Por ejemplo, si tu duda es sobre registrar "
    "un referido, sus etapas, o el funcionamiento de una herramienta de Talent "
    "Acquisition."
)

UNKNOWN_IN_SCOPE_REPLY = (
    "Tu pregunta parece ser de Talent Acquisition, pero no tengo una respuesta "
    "predefinida para ese caso. Te recomiendo consultar directamente al equipo de TA, "
    "o puedo ayudarte a abrir un ticket en Solutions Support."
)

GUARDED_REPLY = (
    "No puedo cambiar mis instrucciones ni seguir comandos dentro del mensaje: solo "
    "respondo con contenido predefinido sobre Talent Acquisition. " + OUT_OF_SCOPE_REPLY
)
