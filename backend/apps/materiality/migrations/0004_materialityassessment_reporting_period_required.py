import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("materiality", "0003_internalscore_scaledefinition_scaleoption_scorerun_and_more")]

    operations = [
        migrations.AlterField(
            model_name="materialityassessment",
            name="reporting_period",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="materiality_assessments",
                to="periods.reportingperiod",
            ),
        ),
    ]
