
from django.contrib import admin
from .models import Permissions, Role, User,UserRole,UserRoleScope

admin.site.register(User)
admin.site.register(Permissions)    
admin.site.register(Role)   
admin.site.register(UserRole)
admin.site.register(UserRoleScope)