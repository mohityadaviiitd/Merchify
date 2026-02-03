# Merchify Frontend

This is a minimal Next.js (TypeScript) frontend for the Merchify backend.

Quick start:

1. Install dependencies

```bash
cd frontend
npm install
```

2. Run dev server

```bash
npm run dev
```

Open http://localhost:3000

Environment variables:
- `NEXT_PUBLIC_API_BASE` (optional) — base URL for the backend API (defaults to http://localhost:8000/api)

Notes:
- Tailwind is configured; run `npx tailwindcss -i ./styles/globals.css -o ./styles/output.css --watch` if you need to rebuild manually, but `next dev` handles styles.
