

from django.contrib import admin

from apps.companies.models import City, Company, Country, State

admin.site.register(Company)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
