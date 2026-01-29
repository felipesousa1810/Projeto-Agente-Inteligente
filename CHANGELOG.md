# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-29

### Added
- **Core Agent**: Deterministic Decision Engine (FSM) implementation.
- **NLU**: Natural Language Understanding module using Pydantic AI.
- **NLG**: Natural Language Generation module for humanized responses.
- **Supabase Integration**:
    - `setup_supabase.py` script for automated project & schema setup.
    - Database schema with RLS policies (`src/db/schema.sql`).
- **Google Calendar Integration**:
    - `GoogleCalendarService` with OAuth 2.0 support.
    - `auth_google.py` script for local token generation.
- **Evolution API**: Webhook handler signatures (skeleton).
- **CI/CD**: GitHub Actions workflow for Tests, Linting (Ruff), and Type Checking (Mypy).
- **Observability**: Structured logging with `structlog` and `logfire` scaffolding.

### Fixed
- Fixed Windows encoding issues in setup scripts.
- Resolved `pydantic-ai` breaking changes (UsageLimits import, output types).
- Added security timeouts to all API requests.
