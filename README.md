# Gym Membership Management System

A **Django + Django REST Framework (DRF)** backend project for managing gym memberships, payments, documents, and activity logs with robust authentication and role-based access control.

---

## Introduction

I am **Biruk Kasahun**, a Software Engineering student passionate about building healthcare and fitness-related software solutions. This project demonstrates my backend development skills by creating a **Gym Membership Management System** that provides:

- User management (admin, staff, members)
- Membership handling with automatic expiry tracking
- Secure payment processing (Chapa integration for Ethiopia)
- Document uploads for member files
- Comprehensive activity logging and audit trail

This project matters because gyms in Ethiopia and beyond often lack **digital management systems**. This backend provides a secure, scalable, and flexible solution.

---

## Problem Statement

Manual gym record-keeping leads to:

- Lost or duplicated membership records
- Difficulty tracking payments
- No centralized history of members
- Limited accountability for staff actions

## Solution Overview

This system solves the above problems by:

- Centralizing all data in a **SQL database**
- Providing RESTful APIs for memberships, users, payments, and documents
- Enforcing **role-based permissions**
- Supporting both **JWT authentication** and **Session Authentication**
- Logging all staff/admin actions for transparency
- Integrating with **Chapa** for secure Ethiopian payment processing

---

## Key Features Implemented

### Security & Authentication Fixes
- **Safe request data access** — Login view uses `.get()` instead of direct dictionary access, preventing `KeyError` crashes on malformed requests
- **Input validation before DB queries** — All validation runs before any database lookups
- **Strict permission classes** — `AdminOnly` no longer leaks access via copy-pasted self-check; `IsSelfOrAdmin` enforces authentication before object-level checks
- **Chapa webhook verification** — Callbacks now verify transactions via Chapa's Verify Payment API instead of trusting webhook payloads; includes amount-mismatch detection

### Chapa Payment Integration
- **Server-side transaction verification** against Chapa's `/v1/transaction/verify/` endpoint
- **Amount tampering protection** — Compares Chapa-reported amount with expected payment amount
- **Idempotent webhook handling** — Duplicate callbacks are safely ignored
- **Comprehensive activity logging** for verified, failed, and mismatched payments

### Data Integrity & Automation
- **Membership expiry command** — `python manage.py check_expiry` scans and flags expired memberships
- **Auto-calculated expiration dates** — Including lifetime plans (100-year far-future date)
- **MemberProfile auto-creation** — Django signal creates a profile whenever a member-role user registers
- **Full activity logging** on all Membership and Payment create/update/delete operations

### API Documentation
- **Interactive Swagger UI** at `/api/docs/` via `drf-spectacular`
- **ReDoc** at `/api/redoc/`
- **OpenAPI schema** at `/api/schema/`

---

## System Architecture

**Core Entities:**

- **Users** — Admin, Staff, Member (custom user model with phone number as username)
- **Memberships** — Linked to users with auto-expiry tracking
- **Payments** — Connected to memberships, Chapa-verified
- **Documents** — Uploaded files per member
- **Activity Logs** — Full audit trail of admin/staff actions

**Relationships:**
```python
users (1) ───< (N) memberships (1) ───< (N) payments
  │                     │
  │                     └───< (N) documents
  │
  └───< (N) activity_logs
```

**Authentication:**
- JWT (primary for APIs)
- Session Auth (for browsable API / demo)

**Integration:**
- Payment Gateway: **Chapa (Ethiopia)**

---

## Key API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | User registration |
| POST | `/api/auth/login/` | JWT authentication |
| POST | `/api/auth/logout/` | Token invalidation |
| POST | `/api/auth/session/login/` | Session authentication (demo) |
| POST | `/api/auth/session/logout/` | Session logout (demo) |
| GET | `/api/auth/session/csrf/` | CSRF token retrieval |

### User Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/users/` | List all users (admin only) |
| GET | `/api/auth/users/<id>/` | Get user details |
| GET | `/api/auth/profile/` | Get current user profile |

### Memberships
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memberships/` | List memberships |
| POST | `/api/memberships/` | Create new membership |
| GET | `/api/memberships/<id>/` | Get membership details |
| PUT/PATCH | `/api/memberships/<id>/` | Update membership |
| DELETE | `/api/memberships/<id>/` | Delete membership (admin only) |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/payments/` | List payments |
| POST | `/api/payments/` | Create new payment record |
| GET | `/api/payments/<id>/` | Get payment details |
| PUT/PATCH | `/api/payments/<id>/` | Update payment |
| DELETE | `/api/payments/<id>/` | Delete payment |
| GET | `/api/payments/chapa/<payment_id>/` | Initiate Chapa payment |
| POST | `/api/payments/chapa/callback/` | Chapa webhook (verified) |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents/` | List documents (members see own) |
| POST | `/api/documents/` | Upload document (staff/admin) |
| GET | `/api/documents/<id>/` | Get document details |
| DELETE | `/api/documents/<id>/` | Delete document (staff/admin) |

### Activity Logs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/activity-logs/` | View logs (admin only) |

### API Documentation
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/docs/` | Interactive Swagger UI |
| GET | `/api/redoc/` | ReDoc documentation |
| GET | `/api/schema/` | OpenAPI schema |

---

## Security & Best Practices

- Role-based permissions (`AdminOnly`, `StaffOrAdmin`, `IsSelfOrAdmin`)
- JWT Authentication for API access
- Session Authentication for browsable API
- CSRF protection for session endpoints
- Server-side Chapa payment verification with amount validation
- Secure file uploads with media isolation
- Comprehensive activity logs for accountability
- Sensitive data sanitization in log metadata

## Tech Stack

- **Backend:** Django 5.2, Django REST Framework
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Auth:** JWT (SimpleJWT) + Session Auth
- **Payments:** Chapa API (Ethiopia)
- **API Docs:** drf-spectacular (Swagger / ReDoc)
- **Version Control:** Git & GitHub

## Future Improvements

- Add a **frontend (React or Next.js)** for member self-service
- Automated email/SMS reminders for expiring memberships
- Enhanced dashboards with charts and analytics
- Full CI/CD deployment pipeline on AWS
- Containerization with Docker

---

## How to Run Locally

```bash
# Clone repo
git clone https://github.com/your-username/gym-membership-system.git
cd gym-membership-system

# Create virtual environment
python -m venv env
source env/bin/activate  # or env\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Management Commands

```bash
# Check and flag expired memberships
python manage.py check_expiry
```

---

## About

This project is a **learning and portfolio project** by **Biruk Kasahun**, demonstrating:

- Backend development with Django and DRF
- RESTful API design and authentication
- Secure payment integration
- Role-based access control and audit logging
