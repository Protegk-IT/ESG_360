# Generated as part of the Module Registry contract stabilization.

from django.db import migrations, models


def canonicalize_module_codes(apps, schema_editor):
    Module = apps.get_model("modules", "Module")

    # The branch originally used aliases that were retired by the platform
    # permission contract. Preserve existing registry configuration whenever
    # possible while upgrading installations that already ran the old seed.
    for legacy_code, canonical_code in (
        ("org", "organization"),
        ("period", "reporting_period"),
    ):
        legacy_module = Module.objects.filter(code=legacy_code).first()
        if legacy_module is None:
            continue

        if Module.objects.filter(code=canonical_code).exists():
            legacy_module.delete()
        else:
            legacy_module.code = canonical_code
            legacy_module.save(update_fields=["code"])

    # Make data valid before adding the database-level invariant. The model
    # already rejects this state for normal writes, but historical direct DB
    # writes should not make an upgrade impossible.
    Module.objects.filter(is_core=True, is_enabled=False).update(is_enabled=True)


class Migration(migrations.Migration):

    dependencies = [
        ("modules", "0003_alter_module_esg_pillar"),
    ]

    operations = [
        migrations.RunPython(canonicalize_module_codes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="module",
            constraint=models.CheckConstraint(
                condition=models.Q(is_core=False) | models.Q(is_enabled=True),
                name="modules_core_requires_enabled",
            ),
        ),
    ]
