import os
import gettext
from functools import lru_cache
from typing import Tuple

# Directory for translations
ROOT = os.path.dirname(__file__)
LOCALES_DIR = os.path.join(ROOT, "locales")

# Supported locales and default (can be overridden by env)
SUPPORTED_LOCALES = [x.strip() for x in os.getenv("SUPPORTED_LOCALES", "en,he").split(",") if x.strip()]
if not SUPPORTED_LOCALES:
    SUPPORTED_LOCALES = ["en", "he"]

DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", SUPPORTED_LOCALES[0])


def _parse_accept_language(header: str) -> list[str]:
    """Parse Accept-Language header and return list of language tags in order."""
    if not header:
        return []
    parts = [p.strip() for p in header.split(",") if p.strip()]
    langs = []
    for p in parts:
        if ";q=" in p:
            lang, q = p.split(";q=", 1)
        else:
            lang = p
        # only primary tag
        langs.append(lang.split("-")[0])
    return langs


@lru_cache(maxsize=32)
def _load_translation(locale: str) -> gettext.NullTranslations:
    """Load gettext translations for a given locale (cached)."""
    try:
        trans = gettext.translation("messages", localedir=LOCALES_DIR, languages=[locale], fallback=True)
    except Exception:
        trans = gettext.NullTranslations()
    return trans


def get_best_locale_from_headers(accept_language_header: str | None, cookie_lang: str | None = None, query_lang: str | None = None) -> str:
    """Return best locale from query param, cookie or Accept-Language header.

    Preference order: query param `lang`, cookie `lang`, Accept-Language header, DEFAULT_LOCALE.
    Matches only primary tags (en, he, fr, etc.) against SUPPORTED_LOCALES.
    """
    # query param has highest priority
    if query_lang:
        q = query_lang.split("-")[0]
        if q in SUPPORTED_LOCALES:
            return q

    if cookie_lang:
        c = cookie_lang.split("-")[0]
        if c in SUPPORTED_LOCALES:
            return c

    langs = _parse_accept_language(accept_language_header or "")
    for l in langs:
        if l in SUPPORTED_LOCALES:
            return l

    return DEFAULT_LOCALE


def get_translator(locale: str) -> Tuple[callable, callable, str]:
    """Return gettext, ngettext and the effective locale."""
    trans = _load_translation(locale)
    gettext_fn = trans.gettext
    ngettext_fn = getattr(trans, "ngettext", lambda s, p, n: s if n == 1 else p)
    return gettext_fn, ngettext_fn, locale
