from django.contrib import admin

from apps.materiality.models import MaterialSubTopic, MaterialTopic, TopicCategory

admin.site.register(TopicCategory)
admin.site.register(MaterialTopic)
admin.site.register(MaterialSubTopic)
