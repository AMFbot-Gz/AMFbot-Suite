# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public issue
2. Email security concerns to: security@amfbot.dev
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to resolve the issue.

## Security Model

### Root Access Module

AMFbot's Root Access module is designed with security as a priority:

- **Explicit Confirmation**: All sudo commands require user confirmation
- **Session Timeouts**: Root sessions expire after 5 minutes
- **Audit Logging**: Every privileged action is logged to `~/.amfbot/audit.log`
- **No Persistence**: Root credentials are never stored

### Network Isolation

- Docker containers run in isolated networks
- External API access is opt-in only
- MCP servers have configurable access scopes

### Data Privacy

- All AI processing happens locally by default
- No telemetry or analytics are collected
- Model weights are downloaded directly from official sources
- User data never leaves your machine

## Best Practices

1. Run AMFbot in a dedicated user account when possible
2. Review audit logs regularly: `cat ~/.amfbot/audit.log`
3. Use environment variables for API keys, never commit them
4. Keep the software updated for security patches
