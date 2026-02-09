# Testing i18n / Language Switching

## Quick Test Guide

### 1. Test Hebrew Manually via URL

You can test translations immediately by adding the `?lang=` query parameter to any URL:

**Hebrew (עברית):**
```
http://localhost:8000/?lang=he
http://localhost:8000/login?lang=he
http://localhost:8000/signup?lang=he
```

**English:**
```
http://localhost:8000/?lang=en
http://localhost:8000/login?lang=en
http://localhost:8000/signup?lang=en
```

### 2. Use Language Switcher in UI

Every page now has a **language switcher** in the top bar:

**On Dashboard (index.html):**
- Located in the top-right header next to Profile/Logout buttons
- Shows: `🇬🇧 EN` | `🇮🇱 HE`
- Click any flag to switch language immediately

**On Login Page (login.html):**
- Located in top-right corner of the screen
- Shows: `🇬🇧 EN` | `🇮🇱 HE`
- Click to switch language before signing in

**On Signup Page (signup.html):**
- Located in top-right corner of the screen
- Shows: `🇬🇧 EN` | `🇮🇱 HE`
- Click to switch language before creating an account

The **active language is highlighted** with a slightly more opaque background.

### 3. Locale Priority Order

The app selects locale in this order (highest priority first):
1. **Query parameter**: `?lang=he` or `?lang=en`
2. **Cookie**: Persisted from previous selection
3. **Accept-Language header**: Browser language preference
4. **Default locale**: English (`en`)

### 4. Running Automated i18n Tests

To verify that all i18n functionality works:

```bash
# Run i18n integration tests
python -m pytest tests/integration/test_i18n.py -v

# Run all tests (including i18n)
python -m pytest tests/ -v
```

Expected output: All 21 i18n tests should **PASS**

### 5. Translation Files Location

English translations:
```
locales/en/LC_MESSAGES/messages.po   # Source text (for translators)
locales/en/LC_MESSAGES/messages.mo   # Compiled binary (used by app)
```

Hebrew translations:
```
locales/he/LC_MESSAGES/messages.po   # Hebrew translations
locales/he/LC_MESSAGES/messages.mo   # Compiled binary
```

### 6. Supported Languages

Currently available:
- **English** (`en`) - 🇬🇧
- **Hebrew** (`he`) - 🇮🇱

To add more languages, see `TRANSLATOR_WORKFLOW.md`

## Features Supported in i18n

✅ Dashboard UI (index.html) - all labels, buttons, messages  
✅ Login page - subtitle, labels, buttons  
✅ Signup page - subtitle, labels, placeholders, buttons  
✅ Profile page - labels  
✅ Error/success messages in routes  
✅ API responses (/health endpoint)  
✅ Dynamic locale detection from request  
✅ Query parameter override (`?lang=he`)  
✅ Language switcher UI in header/topbar  

## Example Translations Currently Available

**English:**
- "Sign in to manage your insurance claims"
- "Upload Receipt"
- "Receipts Stored"
- "API running"

**Hebrew:**
- "התחבר לניהול תביעות הביטוח שלך"
- "העלה קבלה"
- "קבלות מאוחסנות"
- "API פועל"

See `locales/*/LC_MESSAGES/messages.po` for complete list of translated strings.
