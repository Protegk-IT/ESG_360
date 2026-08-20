from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datapoints", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="datapoint",
            name="allow_dynamic_rows",
            field=models.BooleanField(
                default=False,
                help_text="For TABLE datapoints, whether data entry may add rows beyond the fixed catalog rows.",
            ),
        ),
        migrations.AddField(
            model_name="datapoint",
            name="validation_metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Definition-driven validation hints consumed by downstream data capture.",
            ),
        ),
        migrations.AddField(
            model_name="datapointtablecolumn",
            name="validation_metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Definition-driven validation hints for this table column.",
            ),
        ),
    ]
