
from django.contrib import admin
from .models import Permissions, Role, User

admin.site.register(User)
admin.site.register(Permissions)    
admin.site.register(Role)