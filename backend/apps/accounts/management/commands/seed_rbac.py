from django.core.management.base import BaseCommand
from apps.accounts.constants import (
    PERMISSIONS,
    ROLES,
    ROLE_PERMISSIONS,
)
from apps.accounts.models import Permission, Role

class Command(BaseCommand):

    help = "Seed RBAC permissions, roles and role permissions"

    def handle(self, *args, **options):

        self.stdout.write("Seeding permissions...")
        self.seed_permissions()

        self.stdout.write("Seeding roles...")
        self.seed_roles()

        self.stdout.write("Assigning permissions to roles...")
        self.assign_permissions()

        self.stdout.write(
            self.style.SUCCESS(
                "RBAC seeding completed successfully."
            )
        )

    def seed_permissions(self):

        for index, permission in enumerate(PERMISSIONS, start=1):

            code, name, module_code, action = permission

            _, created = Permission.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "module_code": module_code,
                    "action": action,
                    "display_order": index,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created: {code}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Updated: {code}")
                )

    def seed_roles(self):

        for role_code, role_name, description in ROLES:

            _, created = Role.objects.update_or_create(
                role_code=role_code,
                defaults={
                    "role_name": role_name,
                    "description": description,
                    "is_active": True,
                    "is_system": True,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created Role: {role_name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Updated Role: {role_name}")
                )

    def assign_permissions(self):

        for role_code, permission_codes in ROLE_PERMISSIONS.items():

            try:
                role = Role.objects.get(role_code=role_code)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"Role not found: {role_code}"
                    )
                )
                continue

            permissions = Permission.objects.filter(
                code__in=permission_codes
            )

            role.permissions.set(permissions)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Assigned permissions to {role.role_name}"
                )
            )