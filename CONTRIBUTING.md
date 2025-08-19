# Contributing to Outlan Project

Thank you for considering contributing!

## Development Workflow

This project follows Git Flow branching strategy:
- `main` - Stable releases only
- `develop` - Active development branch
- Feature branches - Individual features/fixes

## How to Contribute

1. Fork the repository and create your feature branch from `develop`:
   ```bash
   git checkout develop
   git checkout -b feature/your-feature-name
   ```
2. Make your changes and write clear, concise commit messages.
3. Ensure your code passes all tests and lints (see below).
4. Push your feature branch and submit a pull request to `develop`.
5. After review and testing, changes will be merged to `develop`.
6. Stable releases are periodically merged from `develop` to `main`.

## Code Style

- Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use `black` for formatting and `flake8` for linting.
- Keep functions and classes small and focused.

## Tests

- Add or update unit/integration tests as needed.
- Run all tests with `pytest` before submitting.

## Issues

- Search existing issues before opening a new one.
- Provide as much detail as possible (steps to reproduce, environment, etc).

## Community

- Be respectful and constructive in all communications.
- See the [CODE OF CONDUCT](CODE_OF_CONDUCT.md) if present.