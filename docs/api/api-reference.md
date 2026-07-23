# MasterApp API Reference

## Base URL

```text
http://127.0.0.1:8000/api/
```

## Endpoint Summary

| Module | Method | Endpoint | Purpose |
|---|---|---|---|
| Login | POST | `/api/login/` | Authenticate user |
| Dashboard | GET | `/api/dashboard/` | Load dashboard |
| Job Cards | GET | `/api/jobcards/` | List job cards |
| Job Card Detail | GET | `/api/jobcards/<id>/` | Load one job card |
| Notifications | GET | `/api/notifications/` | List notifications |
| Repair Progress | GET | `/api/repair-progress/<id>/` | Load progress |
| Claims | GET | `/api/claims/` | List claims |

> Verify every path against the project's actual `urls.py`.

## Example Dashboard Response

```json
{
  "stats": {
    "total_jobs": 25,
    "running_jobs": 10,
    "completed_jobs": 8,
    "pending_jobs": 5,
    "delayed_jobs": 2
  },
  "performance": {
    "completion_percentage": 72,
    "efficiency": 80,
    "productivity": 76,
    "average_tat": "4.2 days"
  }
}
```

## Documentation Checklist

- Confirm routes and authentication
- Add request and response examples
- Add filters and pagination
- Add status codes and permissions
- Add API versioning such as `/api/v1/`
