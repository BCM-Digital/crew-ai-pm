# PM Agent Frontend (ShadCN-ready)

- Dev: `npm install && npm run dev`
- Env:
  - `NEXT_PUBLIC_API_BASE` (default `http://localhost:8001`)

This minimal UI uses Tailwind with shadcn-compatible tokens. You can add components via shadcn/ui (e.g., `npx shadcn@latest add button card input`), then replace the basic elements used in `app/page.tsx` with shadcn components.