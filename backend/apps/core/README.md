# Core Module

The `core` app contains reusable building blocks used throughout the ESG 360 platform.

## Features

- BaseModel
- Activity Logging
- RBAC Permission Enforcement
- Scoped Querysets
- Notification utilities
- Current Request middleware

---

# 1. Using BaseModel

All models should inherit from `BaseModel`.

```python
from apps.core.models import BaseModel

class Company(BaseModel):
    company_name = models.CharField(max_length=255)
```

Automatically provides:

- id
- created_at
- updated_at

Example:

```python
company = Company.objects.create(
    company_name="ABC Ltd"
)
```

---

# 2. Activity Logging

Activity logging records create, update and delete operations.

Example ViewSet

```python
from apps.accounts.viewsets import RBACModelViewSet

class CompanyViewSet(RBACModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    module_code = "company"
```

No additional code is required.

Activity logs are created automatically.

---

# 3. RBAC Permission Enforcement

Every protected API should inherit from `RBACModelViewSet`.

Example

```python
class UserViewSet(RBACModelViewSet):

    module_code = "user"

    queryset = User.objects.all()

    serializer_class = UserSerializer
```

Permission mapping

| Action | Permission |
|---------|------------|
| list | user.view |
| retrieve | user.view |
| create | user.create |
| update | user.edit |
| partial_update | user.edit |
| destroy | user.delete |

Custom actions can override permissions.

Example

```python
def get_required_permission(self):
    custom_permissions = {
        "deactivate": "user.edit",
    }

    if self.action in custom_permissions:
        return custom_permissions[self.action]

    return super().get_required_permission()
```

---

# 4. Scoped Access

User permissions are assigned through `UserRoleAssignment`.

Every assignment may be limited by:

- Organization Node
- Module
- Framework
- Valid From
- Valid To

Always filter querysets using the RBAC utilities instead of manually checking roles.

---

# 5. Notifications

Use the notification helper instead of creating notifications manually.

Example

```python
from apps.core.notifications import notify

notify(
    recipient=user,
    notification_type="INFO",
    title="Submission Approved",
    message="Your ESG submission has been approved."
)
```

---

# 6. Authentication APIs

| Endpoint | Description |
|----------|-------------|
| POST /api/auth/login/ | Login |
| POST /api/auth/logout/ | Logout |
| GET /api/auth/me/ | Current user, roles, permissions and scope |
| POST /api/auth/change-password/ | Change password |
| GET /api/accounts/csrf/ | Get CSRF token |

---

# 7. CSRF

Before sending POST, PUT, PATCH or DELETE requests:

1. Call

```
GET /api/accounts/csrf/
```

2. Store the returned token.

3. Send

```
X-CSRFToken: <token>
```

with every write request.

---

# 8. Current User

The `/api/auth/me/` endpoint returns:

- User profile
- Active roles
- Flattened permission list
- Scope summary

Frontend applications should use this endpoint to initialize permissions after login.