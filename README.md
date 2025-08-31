# Gym Membership Management System

A **Django + Django REST Framework (DRF)** backend project for managing gym memberships, payments, documents, and activity logs with robust authentication and role-based access control.

## Introduction

I am Biruk, a Software Engineering student passionate about building healthcare and fitness-related software solutions. This project demonstrates my backend development skills by creating a **Gym Membership Management System** that provides:

* User management (admin, staff, members)
* Membership handling
* Secure payment tracking (Chapa integration for Ethiopia)
* Document uploads
* Activity logging

This project matters because gyms in Ethiopia and beyond often lack **digital management systems**. This backend provides a secure, scalable, and flexible solution.


## Problem Statement

Manual gym record-keeping leads to:

* Lost or duplicated membership records
* Difficulty tracking payments
* No centralized history of members
* Limited accountability for staff actions

## Solution Overview

This system solves the above problems by:

* Centralizing all data in a **SQL database**
* Providing RESTful APIs for memberships, users, payments, and documents
* Enforcing **role-based permissions**
* Supporting both **JWT authentication** and **Session Authentication (Implemented for learning/demo)**
* Logging staff/admin actions for transparency

---

## System Architecture

**Core Entities:**

* **Users** → (Admin, Staff, Member)
* **Memberships** → Linked to users
* **Payments** → Connected to memberships
* **Documents** → Uploaded files per member
* **Activity Logs** → Track admin/staff actions

**Relationships:**
users (1) ───< (N) memberships (1) ───< (N) payments
    │                        │
    │                        └───< (N) documents
    │
    └───< (N) activity_logs

**Authentication:**
* JWT (primary for APIs)
* SessionAuth (only for demo/browsable API/ Login and Logout)

**Integration:**

Payment Gateway: **Chapa (Ethiopia)**

## 🔑 Key API Endpoints

### Authentication Endpoints

`POST /api/auth/register/` – User registration
`POST /api/auth/login/` – JWT authentication
`POST /api/auth/logout/` –Token invalidation
`POST /api/auth/session/login/` – Session authentication (demo)
`POST /api/auth/session/logout/`– Session logout (demo)
`GET /api/auth/session/csrf/ `– CSRF token retrieval

### User Management Endpoints

`GET /api/auth/users/`– List all users (admin only)
`GET /api/auth/users/<id>/`– Get user details
`GET /api/auth/profile/`– Get current user profile

### Membership Endpoints

`GET /api/memberships/`– List memberships
`POST /api/memberships/` – Create new membership
`GET /api/memberships/<id>/` – Get membership details
`PUT /api/memberships/<id>/`–Update membership
`PATCH /api/memberships/<id>/` – Partial membership update
`DELETE /api/memberships/<id>/` – Delete membershipmembership (Admin)

### Payments

`GET /api/payments/` – List payments
`POST /api/payments/` –Create new payment record
`GET /api/payments/<id>/`– Get payment details
`PUT /api/payments/<id>/`–Update payment
`DELETE /api/payments/<id>/`–Delete payment
`GET /api/payments/chapa/<payment_id>/` – Initiate Chapa payment
`POST /api/payments/chapa/callback/` – Chapa payment webhook
`GET /api/payments/success/` – Payment success page
`GET /api/payments/failure/` – Payment failure page


## Security & Best Practices

* Role-based permissions (`AdminOnly`, `StaffOrAdmin`, `IsSelfOrAdmin`)
* JWT Authentication for API access
* Session Authentication for demo/browsable API
* CSRF protection for session endpoints
* Secure file uploads (document management)
* Activity logs for accountability

## Tech Stack

* **Backend:** Django, Django REST Framework
* **Database:** PostgreSQL
* **Auth:** JWT + SessionAuth
* **Payments:** Chapa API
* **Deployment (planned):** AWS (EC2, RDS, S3)
* **Version Control:** Git & GitHub

## Future Improvements

# Documents
* `POST /api/documents/` → Upload documents (Staff/Admin)
# Activity Logs
* `GET /api/activity-logs/` → View logs (Admin only)

* Add a **frontend (React or Next.js)** for member self-service
* Automated email/SMS reminders for expiring memberships
* Enhanced dashboards with charts & analytics
* Full CI/CD deployment pipeline on AWS
* Containerization with Docker



## 📖 How to Run Locally

```bash
# Clone repo
git clone https://github.com/your-username/gym-membership-system.git
cd gym-membership-system

# Create virtual environment
python -m venv env
source env/bin/activate  # or env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run server
python manage.py runserver



##  Q\&A / Closing

This project is a **learning + portfolio project** showing:

* Backend development with Django & DRF
* API design & authentication
* Secure payment integration

