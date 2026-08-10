

from django.contrib import admin

from apps.companies.models import City, Company, Country, Department, State

admin.site.register(Company)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
admin.site.register(Department)
