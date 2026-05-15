<div align="center">

# Modern Gym Management API & Identity Provider

**A production-grade REST API with enterprise-level authentication, authorization, and identity management — engineered for security-first SaaS deployment on AWS.**

[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16-ff1709?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-Ready-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)

</div>

---

## Table of Contents

- [Project Overview](#-project-overview)
- [Security & Identity Architecture](#-deep-dive--security--identity-architecture)
- [Core Architecture](#-core-architecture)
- [API Reference](#-api-reference)
- [Local Setup & Docker](#-local-setup--docker-deployment)
- [Author](#-author)

---

## 🏗 Project Overview

This system is a **full-featured gym management platform backend** that goes far beyond CRUD. It is built with an **"Authentication & Security First"** philosophy — every design decision, from token transport to password storage, follows OWASP recommendations and modern security best practices.

The platform manages the complete gym operations lifecycle — memberships, payments (Chapa gateway), documents, and staff activity — while providing an **identity provider (IdP)** layer that rivals dedicated auth services:

- **Zero-trust token architecture** — JWTs never touch JavaScript; transported exclusively via hardened cookies
- **Adaptive authentication** — Seamless step-up from password → MFA when TOTP is enrolled
- **Social identity federation** — OAuth 2.0 / OpenID Connect with Google and GitHub
- **Defense-in-depth** — Rate limiting, CSRF enforcement, Argon2 hashing, encrypted secrets at rest, immutable audit trail

> **Frontend:** A React SPA will consume this API. The backend is fully decoupled and ready for integration.

---

## 🔐 Deep Dive — Security & Identity Architecture

> *This section represents the core engineering achievement of this repository.*

### 1. Secure Token Storage — HttpOnly Cookie Transport

| Concern | Our Approach |
|---------|-------------|
| **XSS mitigation** | JWTs are stored in `HttpOnly` cookies — completely inaccessible to JavaScript (`document.cookie` returns nothing) |
| **CSRF mitigation** | `SameSite=Lax` + server-side CSRF enforcement on all state-changing requests |
| **Transport security** | `Secure` flag enforced in production (HTTPS only) |
| **Token separation** | Access token (15 min) and refresh token (7 days) stored in separate named cookies |

**Why not `localStorage`?** A single XSS vulnerability in any dependency would expose tokens stored in `localStorage` or `sessionStorage`. Our approach ensures that even if an attacker achieves script execution, they cannot exfiltrate authentication credentials.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Browser (React SPA)                                                 │
│                                                                     │
│  ┌────────────────────┐     ┌────────────────────────────────────┐ │
│  │  JS Application    │     │  Cookie Jar (HttpOnly, Secure)     │ │
│  │  ─────────────     │     │  ──────────────────────────────    │ │
│  │  Cannot read or    │     │  gym_access_token  = eyJ...        │ │
│  │  write auth tokens │     │  gym_refresh_token = eyJ...        │ │
│  └────────────────────┘     └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
         │  API request (cookies auto-attached by browser)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Django API ──► CookieJWTAuthentication ──► CSRF Check ──► View      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2. Session Management & Refresh Token Rotation

The system implements **refresh token rotation with replay detection** — a critical defense against token theft:

```
Login ──► Issue Refresh Token (RT₁) + Access Token (AT₁)
           │
           ├── RT₁ used ──► Blacklist RT₁ in Redis ──► Issue RT₂ + AT₂
           │
           └── RT₁ reused (stolen?) ──► ALERT: Replay detected!
                                         Revoke entire token family
                                         Invalidate UserSession
                                         Audit: TOKEN_REVOKED
```

**Key implementation details:**

- **`UserSession` model** tracks device fingerprint, browser, IP, `token_family` (UUID), and `last_activity`
- **Redis blacklist** (`bl:refresh:<jti>`) provides O(1) lookup for revoked tokens with automatic TTL-based cleanup
- **Token family concept** — every refresh rotation shares a `token_family` UUID; if a blacklisted token is replayed, the *entire family* is revoked, immediately terminating the attacker's session
- **Graceful degradation** — falls back to `LocMemCache` if Redis is unavailable in development

---

### 3. Granular Authorization — RBAC + ABAC Hybrid

The system implements a **dual-layer authorization model** that balances operational simplicity with fine-grained control:

#### Role-Based Access Control (RBAC)

| Role | Access Level |
|------|-------------|
| `Admin` | Full system access, user management, system settings |
| `Manager` | Operational management, member oversight |
| `Trainer` | View assigned members, manage training schedules |
| `Receptionist` | Front-desk operations, check-ins |
| `Member` | Self-service: own profile, membership, payments |

Implemented via composable DRF permission classes (`IsAdmin`, `IsManager`, `IsTrainer`, `IsReceptionist`) that can be combined with bitwise OR for multi-role endpoints.

#### Attribute-Based Access Control (ABAC)

The `IsOwnerOrReadOnly` permission class provides resource-level ownership checks:

```python
# Any authenticated user can read; only the resource owner can write
class IsOwnerOrReadOnly(BasePermission):
    owner_field = "user"  # configurable per-view

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(obj, self.owner_field) == request.user
```

This enables patterns like "members can edit their own profile but not others" without requiring separate endpoints per role.

---

### 4. Advanced Identity — OAuth 2.0 + TOTP MFA

#### Social Login (OAuth 2.0 / OpenID Connect)

```
┌──────────┐         ┌──────────────┐         ┌────────────────┐
│  React   │──code──►│  Django API  │──code───►│ Google/GitHub  │
│  SPA     │         │  /oauth/cb/  │◄─token──│ Token Endpoint │
└──────────┘         └──────┬───────┘         └────────────────┘
                            │
                    fetch userinfo
                    create/update User
                    issue JWT cookies
                            │
                            ▼
                  ┌───────────────────┐
                  │ If MFA enabled:   │
                  │ Return mfa_token  │
                  │ (5 min, signed)   │
                  └───────────────────┘
```

- Supports **Google** and **GitHub** as identity providers
- Handles GitHub's hidden-email edge case via `/user/emails` API
- Creates local accounts on first OAuth login (auto-verified)
- Respects MFA — even OAuth users must complete TOTP if enrolled

#### Multi-Factor Authentication (TOTP)

The MFA implementation follows a **two-phase login** pattern:

| Phase | Endpoint | What Happens |
|-------|----------|-------------|
| **1. Password** | `POST /auth/login/` | Validates credentials → returns `mfa_token` (signed, 5-min TTL) |
| **2. TOTP** | `POST /auth/mfa/verify/` | Validates TOTP code + `mfa_token` → issues JWT cookies |

**Security measures:**

- TOTP secrets encrypted at rest using **Fernet symmetric encryption** (AES-128-CBC + HMAC-SHA256)
- 10 single-use backup codes generated at enrollment, stored as **SHA-256 hashes**
- Backup codes are consumed on use (removed from the hash list)
- MFA token is a Django-signed payload with 5-minute expiry — cannot be forged or reused

---

### 5. System Hardening

| Layer | Implementation |
|-------|---------------|
| **Password hashing** | Argon2id (OWASP primary recommendation) with PBKDF2 fallback for legacy hashes |
| **Rate limiting** | Redis-backed DRF throttles: login (5/min), password reset (3/min), token refresh (10/min), MFA verify (5/min) |
| **CSRF protection** | Enforced on all cookie-authenticated mutations via custom `CookieJWTAuthentication._enforce_csrf()` |
| **Audit logging** | Immutable `AuditLog` model capturing: LOGIN, LOGIN_FAILED, LOGOUT, PASSWORD_RESET, MFA_ENABLED, MFA_DISABLED, MFA_CHALLENGE, TOKEN_REVOKED, SESSION_REVOKED |
| **Structured logging** | JSON-formatted logs with `SensitiveDataFilter` — regex + key-based redaction of passwords, tokens, secrets, API keys |
| **Email security** | Signed, single-use tokens for verification (24h) and password reset (30min); embeds password-hash fragment to prevent reuse |

---

## 🏛 Core Architecture

### Custom User Model

```
User (AbstractBaseUser + PermissionsMixin)
├── email (unique, primary identifier)
├── full_name
├── role (admin | manager | trainer | receptionist | member)
├── is_verified (email confirmation)
├── mfa_enabled (TOTP enrollment status)
├── oauth_provider (google | github | "")
├── profile_image
├── phone_number (optional)
└── timestamps (created_at, last_login)
```

### Entity Relationships

```
User ──┬──► MemberProfile (1:1, member-specific data)
       ├──► MFADevice (1:1, encrypted TOTP secret + backup codes)
       ├──► UserSession (1:N, tracked sessions per device)
       ├──► AuditLog (1:N, immutable security events)
       ├──► Membership (1:N, with auto-expiry tracking)
       │       └──► Payment (1:N, Chapa-verified)
       └──► Document (1:N, uploaded files)
```

### Background Processing (Celery)

Asynchronous tasks powered by Celery + Redis broker:

- Email verification dispatch
- Password reset email delivery
- Membership expiry notifications
- Payment webhook processing

---

## 📡 API Reference

### Authentication & Identity

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|-----------|
| POST | `/api/auth/register/` | Create account + send verification email | Public | — |
| POST | `/api/auth/login/` | Authenticate → JWT cookies or MFA challenge | Public | 5/min |
| POST | `/api/auth/logout/` | Blacklist refresh token, clear cookies | JWT | — |
| POST | `/api/auth/token/refresh/` | Rotate refresh token | Cookie | 10/min |

### Email Verification & Password Reset

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|-----------|
| POST | `/api/auth/verify-email/` | Confirm email with signed token | Public | — |
| POST | `/api/auth/verify-email/resend/` | Re-send verification email | JWT | — |
| POST | `/api/auth/password-reset/` | Request reset email (anti-enumeration) | Public | 3/min |
| POST | `/api/auth/password-reset-confirm/` | Set new password with token | Public | — |

### OAuth 2.0

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/oauth/callback/` | Exchange authorization code → JWT cookies | Public |

### Multi-Factor Authentication

| Method | Endpoint | Description | Auth | Rate Limit |
|--------|----------|-------------|------|-----------|
| POST | `/api/auth/mfa/setup/` | Generate TOTP secret + backup codes | JWT | — |
| POST | `/api/auth/mfa/setup/confirm/` | Confirm setup with first TOTP code | JWT | — |
| POST | `/api/auth/mfa/verify/` | Complete MFA login (step 2) | Public | 5/min |
| DELETE | `/api/auth/mfa/disable/` | Remove MFA device | JWT | — |
| POST | `/api/auth/mfa/backup-codes/regenerate/` | Issue new backup codes | JWT | — |

### User & Profile Management

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/auth/users/` | List all users | Admin |
| GET | `/api/auth/users/<id>/` | User detail | Self or Admin |
| GET | `/api/auth/profile/` | Current user profile | JWT |
| PUT | `/api/auth/me/member-profile/` | Edit own member profile | Owner |

### Business Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| CRUD | `/api/memberships/` | Membership lifecycle management |
| CRUD | `/api/payments/` | Payment records + Chapa integration |
| CRUD | `/api/documents/` | Member document uploads |
| GET | `/api/activity-logs/` | Admin audit trail |

### API Documentation

| Endpoint | Format |
|----------|--------|
| `/api/docs/` | Interactive Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI 3.0 JSON |

---

## 🚀 Local Setup & Docker Deployment

### Prerequisites

- Docker & Docker Compose v2+
- Git

### 1. Clone & Configure

```bash
git clone https://github.com/brook1717/Gym_management.git
cd Gym_management
```

Create a `.env` file in the project root:

```env
# ─────────────────────────────────────────────────────────────────
# Django
# ─────────────────────────────────────────────────────────────────
SECRET_KEY=your-production-secret-key-here
DEBUG=0
ALLOWED_HOSTS=api.yourdomain.com,localhost

# ─────────────────────────────────────────────────────────────────
# Database (PostgreSQL — replace with RDS endpoint for AWS)
# ─────────────────────────────────────────────────────────────────
DATABASE_URL=postgres://gym_user:gym_pass@db:5432/gym_db

# ─────────────────────────────────────────────────────────────────
# Redis (replace with ElastiCache endpoint for AWS)
# ─────────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─────────────────────────────────────────────────────────────────
# OAuth Providers
# ─────────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# ─────────────────────────────────────────────────────────────────
# MFA Encryption (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# ─────────────────────────────────────────────────────────────────
MFA_ENCRYPTION_KEY=your-fernet-key-here

# ─────────────────────────────────────────────────────────────────
# Email (SES in production)
# ─────────────────────────────────────────────────────────────────
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# ─────────────────────────────────────────────────────────────────
# Frontend
# ─────────────────────────────────────────────────────────────────
FRONTEND_URL=http://localhost:3000
```

### 2. Launch with Docker Compose

```bash
# Build and start all services (API, PostgreSQL, Redis, Celery worker)
docker compose up --build -d

# Apply database migrations
docker compose exec api python manage.py migrate

# Create an admin user
docker compose exec api python manage.py createsuperuser

# Verify all services are healthy
docker compose ps
```

### 3. Verify the Stack

```bash
# Health check
curl http://localhost:8000/api/docs/

# Test rate limiting (6th request should return 429)
for i in {1..6}; do
  echo "Attempt $i: $(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/api/auth/login/ -H 'Content-Type: application/json' -d '{"email":"x@y.com","password":"wrong"}')"
done
```

### Services Architecture

| Service | Port | Purpose |
|---------|------|---------|
| `api` | 8000 | Django + Gunicorn (4 workers) |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Cache, rate limits, token blacklist, Celery broker |
| `celery_worker` | — | Async task processing |

<details>
<summary><strong>📋 Local Development (without Docker)</strong></summary>

```bash
cd gym_management

# Virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r ../requirements.txt

# Run with SQLite (default when DATABASE_URL is unset)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> **Note:** Redis must be running locally for rate limiting and token blacklisting. The system gracefully falls back to in-memory cache in DEBUG mode.

</details>

---

## 👤 Author

**Biruk Kasahun**

Software Engineer specializing in backend systems, security architecture, and cloud-native deployments.

[![GitHub](https://img.shields.io/badge/GitHub-brook1717-181717?style=flat-square&logo=github)](https://github.com/brook1717)

---

<div align="center">

*Built with security as a first-class architectural concern, not an afterthought.*

</div>
