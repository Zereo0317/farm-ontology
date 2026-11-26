# URL schemes (canonical map, 2026-11-27)

## Landing (seges.ai, TanStack Start)

- Path locale: /{zh-TW|zh-CN|en|ja|th} (the URL IS the locale).
- Audience: ?for=farmer|research|finance (farmer is the default).
- Legacy compat: ?for=hunger maps to research (querystring shim).
- Social previews: per-locale x per-audience og-images selected by the
  same two parameters.

## Field web (Next.js)

### Locale selection
- Canonical: ?lang= (report + pitch pages read this first).
- Compat: ?locale= accepted on pitch pages with the same meaning.
- Fallback chain: param -> farm-locale cookie (middleware negotiates on
  first visit; explicit user choice is never stomped) -> zh-TW.
- Document language: the SSR shell is "und"; each page that knows its
  language pins documentElement.lang at render (HtmlLang component /
  boundary-walker convention). Values: zh-Hant-TW / zh-Hans-CN / en / ja / th.

### Tool pages (no locale prefix BY DESIGN)
- /walk, /fieldday, /report/biratori-1119, /farm[/...], /pitch/*,
  /demo/biratori live on the FIELD WEB; the worker redirects any
  locale-prefixed form (/{locale}/walk, ...) to the bare path (the page
  handles language via its own switcher).
- Public (no session): login, api/auth, livez, report, fieldday, walk,
  api/boundaries, api/scene-thumb, reports, icon.svg, pitch, demo.
- Everything else requires the OIDC session; farm membership re-checked
  per request.

### Farm deep links
- /farm redirects to /farm/biratori-hokkaido (opaque farm-id slug).
- /farm/{farm_id} is the field sheet for that membership-scoped farm.
- /farm/{lat},{lon} is the legacy coordinate form; without farm_id it
  resolves to the operator farm.