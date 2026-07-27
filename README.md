# 🚗 MasterApp

## Body Shop & Insurance Claim Management System

An enterprise-grade Body Shop Management System built with **Django**,
**PostgreSQL**, **Flutter**, and **Django REST Framework**.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Django](https://img.shields.io/badge/Django-6.x-success)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue)
![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B)

------------------------------------------------------------------------

## Project Overview

MasterApp digitizes complete body shop operations from vehicle inward to
final delivery.

### Core Modules

-   Insurance Claim Management
-   Customer & Vehicle Management
-   Job Card Management
-   Vehicle Inventory
-   Work Allocation
-   Parts Management
-   Reinspection
-   Notifications
-   Reports & Dashboard
-   Role-Based Access Control (RBAC)
-   REST API
-   Flutter Mobile Application

  -----------------------------------------------------------------------
  \## 📚 Documentation

  \### Architecture

  \- [System Architecture](docs/architecture/system-architecture.md) -
  [Insurance Claim Workflow](docs/architecture/claim-workflow.md) - [Job
  Card Workflow](docs/architecture/jobcard-workflow.md) - [RBAC
  Permission Flow](docs/architecture/rbac-flow.md)

  \### API Documentation

  \- [REST API Reference](docs/api/api-reference.md)
  -----------------------------------------------------------------------

# 🏗️ System Architecture

The following diagrams provide a high-level overview of the MasterApp
architecture and workflows.

## 1. System Architecture

![System Architecture](docs/architecture/images/system-architecture.png)

------------------------------------------------------------------------

## 2. Insurance Claim Workflow

![Insurance Claim
Workflow](docs/architecture/images/insurance-claim-workflow.png)

------------------------------------------------------------------------

## 3. Job Card Workflow

![Job Card Workflow](docs/architecture/images/jobcard-workflow.png)

------------------------------------------------------------------------

## 4. Role-Based Access Control (RBAC)

![RBAC Flow](docs/architecture/images/rbac-flow.png)

------------------------------------------------------------------------

## 5. Flutter + Django Integration

![Flutter Django
Integration](docs/architecture/images/flutter-django-integration.png)

------------------------------------------------------------------------

## 6. Database ER Diagram

![Database ER Diagram](docs/architecture/images/database-er-diagram.png)

------------------------------------------------------------------------

## 📸 Application Screenshots

> Save all screenshots inside `docs/screenshots/` using the filenames
> below.

### 🔐 Login

Secure authentication with Role-Based Access Control.

``` text
docs/screenshots/login.png
```

![Login](docs/screenshots/login.png)

------------------------------------------------------------------------

### 📊 Dashboard

Real-time KPIs, technician workload, active jobs, approvals, and
workshop performance.

``` text
docs/screenshots/dashboard.png
```

![Dashboard](docs/screenshots/dashboard.png)

------------------------------------------------------------------------

### 📋 Claim Management

``` text
docs/screenshots/claim-management.png
```

![Claim Management](docs/screenshots/claim_list.png)

------------------------------------------------------------------------

### 🚗 Job Card Management

``` text
docs/screenshots/jobcard.png
```

![Job Card](docs/screenshots/jobcard.png)

------------------------------------------------------------------------

### 🚙 Vehicle Inventory

``` text
docs/screenshots/vehicle-inventory.png
```

![Vehicle Inventory](docs/screenshots/vehicle-inventory.png)

------------------------------------------------------------------------

### 👨‍🔧 Work Allocation

``` text
docs/screenshots/work-allocation.png
```

![Work Allocation](docs/screenshots/work-allocation.png)

------------------------------------------------------------------------

### 🛠 Repair Progress

``` text
docs/screenshots/repair-progress.png
```

![Repair Progress](docs/screenshots/repair-progress.png)
------------------------------------------------------------------------
### 🛠 Parts Requisition & Full Filled Process

``` text
docs/screenshots/part-process.png
```

![Part Process](docs/screenshots/part-process.png)
------------------------------------------------------------------------

### 📈 Body Shop Control Board

``` text
docs/screenshots/control-board.png
```

![Control Board](docs/screenshots/control-board.png)

------------------------------------------------------------------------

### 📑 Reports & Analytics

``` text
docs/screenshots/reports.png
```

![Reports](docs/screenshots/reports.png)

------------------------------------------------------------------------

### 🔒 Role-Based Access Control

``` text
docs/screenshots/rbac.png
```

![RBAC](docs/screenshots/rbac.png)

------------------------------------------------------------------------

## 📱 Flutter Mobile Application

### 📲 Mobile Login

![Flutter Login](docs/screenshots/flutter-login.png)

### 📱 Mobile Dashboard

![Flutter Dashboard](docs/screenshots/flutter-dashboard.png)

### 🚘 Mobile Repair Progress

![Flutter Repair Progress](docs/screenshots/flutter-repair-progress.png)

------------------------------------------------------------------------

## Technology Stack

### Backend

-   Python
-   Django
-   Django REST Framework
-   PostgreSQL

### Frontend

-   HTML
-   Bootstrap
-   JavaScript

### Mobile

-   Flutter

------------------------------------------------------------------------

## Installation

``` bash
git clone https://github.com/anilshinde0806-stack/MasterApp.git
cd MasterApp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

------------------------------------------------------------------------

## Current Features

-   ✅ Insurance Claims
-   ✅ Job Cards
-   ✅ Vehicle Inventory
-   ✅ Work Allocation
-   ✅ Notifications
-   ✅ Reports
-   ✅ Dashboard
-   ✅ RBAC
-   ✅ REST API
-   ✅ PostgreSQL
-   ✅ Flutter Integration

------------------------------------------------------------------------

## Roadmap

-   WhatsApp Customer Portal
-   Insurance Renewal
-   Timeline Tracking
-   Push Notifications
-   CI/CD
-   Production Deployment

------------------------------------------------------------------------

## Author

**Anil Shinde**

GitHub: https://github.com/anilshinde0806-stack
