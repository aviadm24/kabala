# Project Intentions – UI & Product Direction

## High-level goal
This application is a SERVICE that actively helps users get insurance reimbursements.
It is not a CRUD tool, admin panel, or document storage app.

The UI should always communicate:
- "We are handling this for you"
- "You don't need to understand insurance"
- "There is progress even when nothing is required from you"

---

## UI principles
- Mobile-first, calm, trustworthy design
- One main column, max width ~700px
- Use cards instead of tables
- Prefer progress indicators over raw data
- Avoid technical language
- Avoid dashboards that look like admin tools

---

## Core UI concept
Each uploaded receipt becomes a CLAIM with a lifecycle:
uploaded → processing → ready_for_submission → submitted → approved/rejected

UI elements should be driven by claim status.

Do not expose internal status values directly.
Always map them to human-friendly messages.

---

## Template rules (Jinja2)
- Keep templates presentation-only
- No business decisions in templates
- All user-visible strings must use gettext (_())
- No string concatenation in translations
- Use includes for reusable components (e.g. claim cards, status indicators)

---

## i18n rules
- All text must be translatable (.po/.mo)
- Use placeholders instead of building strings
- English is the source language

---

## What to avoid
- Tables for main flows
- Raw IDs or internal enums in UI
- Asking users to choose insurance logic
- Overloading users with options
- Technical error messages without explanation

---

## Long-term direction
This UI must support:
- Automation of claims
- Human-in-the-loop workflows
- Future AI explanations
- Email/WhatsApp notifications

Design everything so it can evolve without redesign.
