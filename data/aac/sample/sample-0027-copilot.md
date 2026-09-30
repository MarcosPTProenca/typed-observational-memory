# Copilot / AI Agent Instructions for Food-Reservation

This file helps AI coding agents become productive fast in this repository. Keep instructions concise and concrete — reference files and patterns that actually exist here.

1) Big-picture architecture
- Backend: Express-based API in `backend/` (entry: `backend/index.js`). Routes live under `backend/src/routes/`, controllers in `backend/src/controllers/`, and a repository abstraction under `backend/src/repositories/` with a `RepositoryFactory` used to switch implementations (JSON file vs Mongo). The `menus` endpoints are handled by controllers that use multer `upload.single("image")` for image handling.
- Frontend: React app in `frontend/` (CRA-like). Primary client code is under `frontend/src/`. Admin UI lives in `frontend/src/pages/admin/` (example: `adminhomes.jsx`). API client is `frontend/src/lib/api.js` which uses `fetch`, `credentials: 'include'`, and automatically detects `FormData` (do not set `Content-Type` manually).
- Integration: Image storage can be local filesystem or Cloudinary. Configuration is driven by `backend/.env` (e.g., `IMAGE_STORAGE_TYPE`, `CLOUDINARY_*`).
- JWT authentication is used—frontend relies on saved tokens in browser local storage; the API client includes `credentials: 'include'` (always double check this).

2) Important files and patterns to read first
- `backend/src/routes/*.js` — route declarations (middleware + controllers). Look for `upload.single("image")` to find file upload behavior.
- `backend/src/controllers/*` — controllers implement business logic and call repository methods.
- `backend/src/repositories/repository.factory.js` — switches between file-backed and Mongo-backed repositories.
- `backend/.env.examples` — shows required environment variables for the real `.env` file (Cloudinary keys, `IMAGE_STORAGE_TYPE`).
- `frontend/src/lib/api.js` — centralized fetch wrapper. Key behaviors:
  - Detects `FormData` and avoids setting `Content-Type` to let browser add the boundary.
  - Sends `credentials: 'include'` for auth.
  - Unwraps inconsistent backend response formats.
- `frontend/src/pages/admin/adminhomes.jsx` — example admin page that edits menu items; shows how image replacement and FormData should be built and sent.

3) Project-specific conventions and behaviors
- RepositoryFactory pattern: code uses a factory to get repository implementations;
- Cookie-first auth: never rely on localStorage tokens in production — code includes a development fallback but expects httpOnly cookies.
- File uploads: backend expects multipart/form-data for routes with multer; the frontend must not set `Content-Type` header explicitly when sending FormData (the client `api.js` handles this). Setting `Content-Type` manually will break boundary generation.
- Tests: backend tests under `backend/src/__tests__` use `supertest` and the app export from `backend/index.js`. Tests sometimes directly use repository factories to create test fixtures.

4) Developer workflows & commands (where to look)
- When running backend npm tests locally always comment out the `MONGO_URI` environment variable in the `.env` file at the `./backend` folder make sure it was not declared and just un-comment it back after testing, Also skip cloudinary test cases if at least one of the following environment variables is not set, is empty or is not present in the `.env` file: `IMAGE_STORAGE_TYPE`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` and `CLOUDINARY_API_SECRET`.
- Root-level `package.json` and `backend/package.json` and `frontend/package.json` contain scripts for start/test/build. Inspect them for exact commands. Typical flows:
  - Backend dev: `cd backend && npm run dev` (nodemon/express)
  - Frontend dev: `cd frontend && npm start` (CRA)
  - Run tests: `cd backend && npm test` (jest + supertest)
- GitHub Actions workflows are in `.github/workflows/` (see `backend-ci.yml`, `frontend-ci.yml`) for CI hints.

5) Common fixes & pitfalls for agents
- When fixing upload issues, check `frontend/src/lib/api.js` for FormData handling and ensure headers are not overridden. Example bug: setting `Content-Type: multipart/form-data` manually causes `Multipart: Boundary not found` on the server.
- Respect repository patterns: prefer using repository factory for data operations in controllers/tests rather than direct file/db access.
- For image storage, check `IMAGE_STORAGE_TYPE` env var and Cloudinary config before changing storage logic.

6) Example tasks and where to implement them
- Add a new menu field: update repository schema, controller update logic, and frontend edit modal and `adminhomes.jsx` FormData construction.
- Fix upload handling: read `api.js` and remove manual `Content-Type` header when sending FormData.
- Add tests: mirror existing test patterns in `backend/src/__tests__`, use `createTestAdmin`, `getAuthHeaders`, and `RepositoryFactory` helpers.

7) Communication with maintainers
- CI and tests run in GH Actions: check `.github/workflows/*` for the OS/node versions.
- Sensitive values are in `backend/.env` (do not commit secrets). Cloudinary creds are present in `.env` in this repo — treat accordingly.

8) Additional Rules
- there are also additional rules for AI agents in the `./backend/AGENTS.md` and `./frontend/AGENTS.md`, make sure to check those rules too.