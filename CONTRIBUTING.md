# Contributing to Agentic RAG

Thank you for your interest in contributing! This project is a reference RAG implementation — contributions that improve its value as a learning template are especially welcome.

---

## Reporting Bugs

Found a bug? Please open an issue in the [Issues tracker](https://github.com/giladresisi/agentic-rag/issues).

Include:
- A clear title and description of the problem
- Steps to reproduce
- Expected vs. actual behaviour
- Environment details (OS, browser, Python version, etc.)
- Relevant logs or screenshots, if available

Check existing issues before opening a new one to avoid duplicates.

---

## Suggesting Features or Fixes

Feature requests and bug fixes should be submitted as a pull request:

1. Fork the repository
2. Create a new branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-fix-description
   ```
3. Make your changes (see [Setting Up for Local Development](#setting-up-for-local-development))
4. Commit with a clear, descriptive message
5. Push your branch and open a Pull Request against `main`

In the PR description, explain:
- What problem it solves or what it adds
- Any decisions or trade-offs made
- How you tested it

---

## Setting Up for Local Development

Follow [SETUP.md](https://github.com/giladresisi/agentic-rag/blob/main/SETUP.md) for complete instructions on running the backend and frontend locally, configuring environment variables, and running the test suite.

---

## Pull Request Guidelines

- Keep PRs focused — one concern per PR
- PRs that break existing tests will not be merged
- Update relevant documentation (README, SETUP.md, inline comments) if your change affects behaviour or configuration
- Be responsive to review feedback

---

## Code Style

**Backend (Python):**
- Follow PEP 8
- Use type hints
- No `print()` statements in production code — use the logging framework or store errors in the database
- New endpoints should include at least one test in `backend/tests/`

**Frontend (TypeScript/React):**
- Follow the existing ESLint configuration
- Prefer editing existing components over creating new ones unless clearly necessary

---

## Contact

For anything not covered by issues or pull requests — questions about the architecture, integration enquiries, or anything else — email the maintainer directly at [giladresisi@gmail.com](mailto:giladresisi@gmail.com).
