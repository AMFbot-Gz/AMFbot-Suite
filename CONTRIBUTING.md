# Contributing to AMFbot Suite

Thank you for your interest in contributing to AMFbot! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use the issue templates when available
3. Provide detailed reproduction steps
4. Include system information (OS, Node.js version, hardware)

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes with clear commit messages
4. Add tests for new functionality
5. Ensure all tests pass: `npm test`
6. Submit a pull request

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Test additions
- `chore:` Maintenance

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/amfbot-suite.git
cd amfbot-suite

# Install dependencies
npm install

# Install Python dependencies
cd modules/media-gen && pip install -e ".[dev]"

# Run in development mode
npm run dev

# Run tests
npm test
```

## Code Style

- **TypeScript**: We use ESLint and Prettier
- **Python**: We use Black and Ruff
- Run `npm run format` before committing

## Adding MCP Servers

To add a new pre-configured MCP server:

1. Create a JSON file in `mcp-hub/servers/`
2. Add the server to `AVAILABLE_SERVERS` in `mcp-hub/installer.ts`
3. Document in `docs/mcp-servers.md`

## Testing

- Write unit tests for new features
- Test on multiple platforms when possible
- Include integration tests for MCP servers

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
