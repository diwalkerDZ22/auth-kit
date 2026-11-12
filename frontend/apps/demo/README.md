# auth-kit : application de démo

Montre comment un projet intègre `@auth-kit/react` (dossier `packages/auth-kit`).

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 ; /api est relayé vers http://127.0.0.1:8000
```

- `src/main.tsx` : client (`createAuthClient`), `QueryClientProvider`, `AuthProvider`, `AuthUIProvider`.
- `src/App.tsx` : routeur avec `createAuthRoutes()` et les routes du projet.
- `src/Layout.tsx` : en-tête (navigation, sélecteur de thème, compte).
- `src/HelloPage.tsx` : appel d'une route métier protégée avec `client.request()`.

Voir `docs/Bibliotheque.md` pour l'intégration dans un autre projet.
