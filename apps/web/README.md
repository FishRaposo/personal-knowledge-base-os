# Personal Knowledge Base OS dashboard

The Next.js 14 / React 18 / TypeScript dashboard is the offline-capable frontend for the local knowledge-base API. It preserves the existing search, note, graph, chat, and tags views while adding vault workspace selection, note editing, dangling-link indicators, watcher/index status, saved searches, tag filters, deterministic flashcards, and review actions.

## Install and run

```bash
npm ci
npm run dev
```

The default API URL is `http://localhost:8000` (`NEXT_PUBLIC_API_URL`). Run the backend with `python -m apps.api.src.main` from the repository root. No database, broker, provider key, or watcher is needed for dashboard demo mode.

## Live and demo behavior

The dashboard is live-first. It uses the FastAPI API when reachable, including `vault_id=default` compatibility and additive vault/event/card routes. If the connection cannot be made, bundled fixtures provide an explorable demo for every dashboard state. Server 4xx/5xx responses remain visible and are never silently converted to demo success.

SSE updates watcher, index, and editor state when `/events` is available. Clients retain a polling/replay fallback; watcher startup is explicit and opening a page never watches the filesystem. Demo write actions stay local to fixtures and are marked as non-persistent.

## API surfaces used

Legacy endpoints: `/notes/index`, `/notes/search`, `/notes/{id}`, `/notes/{id}/backlinks`, `/graph`, `/tags`, `/stats`, `/notes/chat`.

Additive endpoints: `/vaults`, `PATCH /notes/{id}`, `/saved-searches`, `/flashcards`, `/watchers/{vault_id}`, `/events`, and `/events/replay`. The UI sends the active vault identifier with every scoped operation and relies on the server for vault-root/symlink safety.

## Verification

```bash
npm test -- --run
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e -- --project=chromium
```

Component tests cover live/demo/error transitions and dashboard fixtures; Playwright smoke runs against the offline-capable UI. Final executed counts belong in the portfolio receipt after the clean-environment gates pass.
