from django.contrib import admin

from apps.datapoints.models import Datapoint, DatapointCategory, DatapointOption, DatapointTableColumn, DatapointTableRow, Unit, UnitFamily

# Register your models here.

admin.site.register(UnitFamily)
admin.site.register(Unit)
admin.site.register(DatapointCategory)
admin.site.register(Datapoint)
admin.site.register(DatapointOption)
admin.site.register(DatapointTableColumn)
admin.site.register(DatapointTableRow)

