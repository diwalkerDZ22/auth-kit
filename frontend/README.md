# auth-kit : frontend

React + TypeScript (Vite), Tailwind, React Router, TanStack Query, React Hook Form + Zod.

```bash
npm install
npm run dev      # http://localhost:5173 ; /api est relayé vers http://127.0.0.1:8000
npm run build
npm run lint
```

- `src/auth/` : module réutilisable (client API, `AuthProvider`, gardes, pages, `authRoutes`). À copier dans un autre projet.
- `src/app/` : coquille de démo (layout, accueil, routeur).

Voir `docs/Sprint6-Frontend.md` pour les choix (cookie httpOnly, CSRF, proxy).
