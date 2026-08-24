from django.contrib import admin

from apps.calculations.models import CalculationRule, EmissionFactor, EmissionFactorSource

admin.site.register(EmissionFactorSource)
admin.site.register(EmissionFactor)
admin.site.register(CalculationRule)
