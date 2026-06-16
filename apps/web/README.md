# Knowledge Base OS — Web Dashboard

The flagship front end for **personal-knowledge-base-os**: a local-first personal
knowledge base over a vault of markdown notes. Search, browse, visualize, and chat
with your notes — backed by wikilinks, a backlinks graph, and grounded citations.

Built with **Next.js 14 (App Router)**, **React 18**, **TypeScript**,
**Tailwind CSS**, **lucide-react**, **recharts**, **react-markdown**, and
**react-force-graph-2d**.

## Pages

| Route          | What it does |
| -------------- | ------------ |
| `/`            | Landing / overview of the product. |
| `/search`      | Keyword / semantic / hybrid search (`GET /notes/search`) with ranked, scored results. |
| `/notes/[id]`  | Markdown note viewer (`GET /notes/{id}`) — renders content, tags, outbound links, and backlinks (`GET /notes/{id}/backlinks`). |
| `/graph`       | Interactive force-directed graph of notes + wikilinks (`GET /graph`); click a node to inspect and open it. |
| `/chat`        | Chat with citations (`POST /notes/chat`) — grounded answers with inline `[n]` source notes. |
| `/tags`        | Tag browser (`GET /tags`) — a tag cloud with note counts; select a tag to list its notes. |

### Endpoints consumed

`GET /notes/search`, `GET /notes/{id}`, `GET /notes/{id}/backlinks`, `GET /graph`,
`GET /tags`, `GET /stats`, `POST /notes/chat`.

## Getting started

```bash
npm install
npm run dev        # http://localhost:3000
```

By default the app talks to a backend at `http://localhost:8000`. To run the
FastAPI backend (from the repo root):

```bash
# offline-first: boots with no DB / no API key
python -m apps.api.src.main      # serves on :8000
# (optionally) docker compose up postgres redis   # for persistence
```

### Environment

| Variable             | Default                 | Purpose |
| -------------------- | ----------------------- | ------- |
| `NEXT_PUBLIC_API_URL`| `http://localhost:8000` | Base URL of the FastAPI backend. |

Copy `.env.example` to `.env.local` to override.

## Demo mode (no backend required)

Every view is **fully explorable with no backend running**. The app is
**live-first**: it always tries the real API, and only on a *network/connection*
failure does it fall back to **bundled demo fixtures** that mirror the backend's
demo vault. When that happens, a visible **"Demo mode — bundled sample data"**
badge appears on the affected view.

- Real HTTP **4xx/5xx** responses are **not masked** — they surface as true error
  states (e.g. opening a non-existent note shows a 404 "Note not found" view).
- Write actions (chat) in demo mode show an explanatory
  **"Demo — not persisted"** notice.

The fixtures live in `src/lib/mockData.ts` and re-implement the backend's
keyword/semantic/hybrid ranking, graph, tags, backlinks, and simulated cited chat
so demo mode stays self-consistent across pages.

## Testing

```bash
npm run test        # Vitest + @testing-library/react (jsdom) — pass with NO backend
npx tsc --noEmit    # type-check
npm run build       # production build
npm run test:e2e    # Playwright smoke tests over the demo-mode UI
```

Component/unit tests cover the search, note, graph, chat, and tags building
blocks, the demo-mode data layer, and the API client's live → demo fallback and
4xx surfacing. The Playwright spec (`e2e/smoke.spec.ts`) drives the demo-mode UI
end to end.

## Docker

A `web` service is wired into the repo-root `docker-compose.yml`:

```bash
docker compose up web      # http://localhost:3000
```

It runs in dev mode and, by default, points `NEXT_PUBLIC_API_URL` at a backend on
the host (`http://host.docker.internal:8000`). With no backend it simply runs in
demo mode.
