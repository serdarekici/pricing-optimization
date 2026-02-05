# Security & Privacy

This repository is designed as a **portfolio/demo project**.

## What must NOT be committed
- Database credentials, connection strings, passwords, tokens, API keys
- Private endpoints / internal hostnames / IP addresses
- Customer-identifiable data, exports, dumps, screenshots with sensitive info
- Certificates or keys (`*.pem`, `*.key`, `*.p12`)

## Safe configuration pattern
- Put secrets in `.env` locally (ignored by git)
- Use placeholders in `config.example.*` / `.env.example`
- Use environment variables in code (e.g., `os.getenv("DB_HOST")`)

If you find a secret in this repo, rotate it immediately and remove it from git history.
