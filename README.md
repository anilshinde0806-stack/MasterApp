# MasterApp

## Body Shop and Insurance Claim Management System

MasterApp is a full-stack body shop management system built for automobile workshops, insurance claim departments, service advisors, surveyors, technicians, and managers.

The application manages the complete workflow from vehicle entry and insurance claim registration to job-card creation, repair allocation, progress tracking, quality checks, invoicing, and vehicle delivery.

---

## Project Overview

MasterApp is designed to digitize and simplify body shop operations.

It provides centralized management for:

* Insurance claims
* Customers and vehicles
* Job cards
* Repair work allocation
* Parts ordering
* Vehicle inventory
* Survey and approval tracking
* Reinspection
* Notifications
* Reports and dashboards
* Role-based access control
* Mobile application APIs

---

## Main Features

### Claim Management

* Register new insurance claims
* Track claim numbers and insurance claim numbers
* Assign insurance companies and surveyors
* Track claim stages
* Record survey, approval, liability, and invoice information
* Upload assessment and liability documents
* Monitor claim turnaround time

### Job Card Management

* Generate job cards from approved claims
* Record vehicle inward details
* Assign service advisors
* Track repair status
* Record estimated and expected delivery dates
* Maintain labour and parts totals
* Generate printable job-card PDFs
* Maintain job-card PDF versions

### Vehicle Inventory

* Capture vehicle condition during inward
* Record accessories and available items
* Mark vehicle damage on a graphical vehicle layout
* Record tyre condition
* Record fuel level and odometer reading
* Upload vehicle condition photographs

### Work Allocation

* Allocate repair work to technicians
* Assign denting, painting, mechanical, and other work
* Track work progress
* Record completion status
* Monitor running, pending, delayed, and completed jobs

### Parts Management

* Create parts-order headers
* Add required parts
* Track ordered and pending parts
* Maintain manual part entries
* Link parts orders with job cards

### Reinspection

* Schedule vehicle reinspection
* Upload reinspection photographs
* Track reinspection completion
* Organize files using claim-based folders

### Notifications

* User-specific notifications
* Unread-notification counter
* Web notification polling
* Mobile notification API
* Claim and job-card related alerts

### Reports and Dashboard

* Total jobs
* Running jobs
* Completed jobs
* Pending jobs
* Delayed jobs
* Completion percentage
* Productivity and efficiency
* Average turnaround time
* Surveyor performance
* Claim-stage analysis

### Role-Based Access Control

* Dynamic menu permissions
* Role-based module access
* User-specific menu permissions
* Separate access for administrators, managers, advisors, and employees
* Superuser access to all modules

### REST API

The project provides REST APIs for the Flutter mobile application.

Current API areas include:

* Authentication
* Dashboard
* Job cards
* Notifications
* Recent work
* Quick actions
* Repair progress

---

## Technology Stack

### Backend

* Python
* Django
* Django REST Framework
* PostgreSQL

### Frontend

* HTML
* CSS
* JavaScript
* Bootstrap
* Font Awesome

### Mobile Application

* Flutter
* Dart
* Android

### Development Tools

* PyCharm
* PostgreSQL
* pgAdmin
* DataGrip
* Git
* GitHub

---

## Project Structure

```text
MasterApp/
├── apps/                 # Modular Django applications and services
├── config/               # Django project configuration
├── core/                 # Core models, forms, views and migrations
├── docs/                 # Project documentation
├── erp/                  # ERP-related components
├── mobile_api/           # REST APIs for the Flutter application
├── rbac/                 # Role-based access control
├── reports/              # Reports and analytics
├── static/               # Source static files
├── tools/                # Utility scripts and tools
├── manage.py             # Django management command entry point
├── requirements.txt      # Python dependencies
├── render.yaml           # Render deployment configuration
├── run_waitress.py       # Waitress production server runner
└── .gitignore            # Git ignore configuration
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/anilshinde0806-stack/MasterApp.git
cd MasterApp
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

Example:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_NAME=masterapp
DATABASE_USER=postgres
DATABASE_PASSWORD=your-database-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

Do not commit the `.env` file to GitHub.

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## PostgreSQL Setup

Create a PostgreSQL database before running migrations.

Example:

```sql
CREATE DATABASE masterapp;
```

Update the `.env` file with the correct database name, username, password, host, and port.

---

## Static Files

For production deployment, run:

```bash
python manage.py collectstatic
```

Generated files inside `staticfiles/` are excluded from Git.

---

## Media Files

Uploaded customer documents, claim photographs, job-card PDFs, and other media files are stored locally inside the `media/` directory.

The `media/` directory is excluded from Git to prevent customer information and uploaded files from being committed.

---

## Flutter Mobile Application

The Flutter mobile application is maintained separately from this repository.

The mobile app communicates with MasterApp using Django REST APIs.

Mobile functionality includes:

* User login
* Dashboard
* Performance summary
* Quick actions
* Recent work
* Job-card details
* Repair progress
* Notifications

A link to the Flutter repository will be added after it is published.

---

## Security

The following files and folders are intentionally excluded from Git:

* `.env`
* Virtual environments
* SQLite database files
* PostgreSQL credentials
* Media uploads
* Generated static files
* Python cache files
* Database exports
* IDE configuration
* Log files

Never commit production credentials, API keys, WhatsApp tokens, customer documents, or database backups.

---

## Development Roadmap

Planned improvements include:

* WhatsApp interactive customer menu
* Insurance renewal workflow
* Customer verification by mobile number
* Vehicle verification by registration number
* Claim-status enquiry through WhatsApp
* Advanced body shop control board
* Technician performance reports
* Surveyor turnaround-time reports
* Cloud media storage
* Automated testing
* CI/CD deployment
* Mobile push notifications
* Production deployment
* Flutter application release

---

## Current Status

The project is under active development.

Completed areas include:

* Django web application
* PostgreSQL integration
* Claim workflow
* Job-card workflow
* Work allocation
* Vehicle inventory
* Parts orders
* Reinspection
* Notifications
* Role-based access control
* Dashboard REST API
* Flutter dashboard integration

---

## Author

**Anil Shinde**

GitHub: `anilshinde0806-stack`

---

## License

This project is currently maintained as a private or proprietary application.

A formal license can be added later based on the intended commercial or open-source use.
