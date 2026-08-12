from django.contrib import admin

from apps.materiality.models import MaterialSubTopic, MaterialTopic, MaterialityAssessment, ScaleDefinition, ScaleOption, Stakeholder, StakeholderGroup, Survey, SurveyQuestion, TopicCategory,AssessmentTopic,SurveyInvitation,SurveyResponse

admin.site.register(TopicCategory)
admin.site.register(MaterialTopic)
admin.site.register(MaterialSubTopic)
admin.site.register(MaterialityAssessment)
admin.site.register(AssessmentTopic)
admin.site.register(StakeholderGroup)
admin.site.register(Stakeholder)
admin.site.register(Survey)
admin.site.register(ScaleDefinition)
admin.site.register(ScaleOption)
admin.site.register(SurveyQuestion)
admin.site.register(SurveyInvitation)
admin.site.register(SurveyResponse)
