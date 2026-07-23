# MasterApp System Architecture

```mermaid
flowchart LR
    Web[Web Users] --> Django[Django Web App]
    Mobile[Flutter App] --> API[Django REST API]
    Django --> Services[Application Services]
    API --> Services
    Services --> Models[Django Models]
    Models --> DB[(PostgreSQL)]
    Services --> Media[Media and Documents]
    Services --> WA[WhatsApp Integration]
```

## Main Layers

- Presentation: Django templates, Bootstrap, JavaScript, Flutter
- Application: claim, job-card, dashboard, notification and RBAC services
- Data: Django models and PostgreSQL
- Infrastructure: storage, logging, caching, scheduling and integrations
