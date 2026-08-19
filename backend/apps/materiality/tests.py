from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User, UserRoleAssignment
from apps.companies.models import Company
from apps.periods.models import ReportingPeriod
from apps.organizations.models import OrgNode
from apps.materiality.models import (
    AssessmentTopic, MaterialSubTopic, MaterialTopic, MaterialityAssessment,
    ScaleDefinition, ScaleOption, Stakeholder, StakeholderGroup, Survey,
    SurveyGroupLink, SurveyInvitation, SurveyQuestion, SurveyResponse,
    SurveySubmission, TopicCategory, InternalScore, ScoreRun,
)
from apps.materiality.services.scoring import run_scoring


class MaterialityWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="manager", password="test-pass")
        self.company = Company.objects.create(company_name="Example Co", company_code="EXAMPLE", contact_person="Manager", email="manager@example.test", mobile_number="1234567890")
        self.period = ReportingPeriod.objects.create(name="FY 2026", period_type="ANNUAL", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31))
        self.assessment = MaterialityAssessment.objects.create(company=self.company, reporting_period=self.period, name="FY26", mode="SINGLE", created_by=self.user)
        category = TopicCategory.objects.create(code="E", name="Environmental")
        topic = MaterialTopic.objects.create(category=category, name="Climate")
        subtopic = MaterialSubTopic.objects.create(topic=topic, name="Emissions")
        self.assessment_topic = AssessmentTopic.objects.create(assessment=self.assessment, subtopic=subtopic)
        self.impact_scale = ScaleDefinition.objects.create(dimension="IMPACT", name="Impact")
        self.importance_scale = ScaleDefinition.objects.create(dimension="STAKEHOLDER_IMPORTANCE", name="Importance")
        for scale in (self.impact_scale, self.importance_scale):
            for value in range(1, 6):
                ScaleOption.objects.create(scale=scale, value=value, label=str(value))
        self.survey = Survey.objects.create(assessment=self.assessment, title="Survey", status="OPEN")
        self.impact_question = SurveyQuestion.objects.create(survey=self.survey, assessment_topic=self.assessment_topic, scale=self.impact_scale, dimension="IMPACT", question_text="Impact?", display_order=1)
        self.importance_question = SurveyQuestion.objects.create(survey=self.survey, assessment_topic=self.assessment_topic, scale=self.importance_scale, dimension="STAKEHOLDER_IMPORTANCE", question_text="Important?", display_order=2)
        self.group = StakeholderGroup.objects.create(assessment=self.assessment, name="Community", weight=Decimal("100"))

    def _answer_and_submit(self, token, response_token=None, value=4):
        payload = {"response_token": response_token} if response_token else {}
        initial = self.client.get(f"/api/public/materiality/survey/{token}/", payload)
        self.assertEqual(initial.status_code, 200)
        response_token = initial.data["response_token"]
        for question in (self.impact_question, self.importance_question):
            response = self.client.post(f"/api/public/materiality/survey/{token}/answer/", {"response_token": response_token, "question": str(question.id), "value": value}, format="json")
            self.assertIn(response.status_code, (200, 201))
        submitted = self.client.post(f"/api/public/materiality/survey/{token}/submit/", {"response_token": response_token}, format="json")
        self.assertEqual(submitted.status_code, 200)
        return response_token

    def _grant_materiality_access(self, *actions):
        role = Role.objects.create(role_code="materiality_manager", role_name="Materiality manager")
        for action in actions:
            permission = Permission.objects.create(
                code=f"materiality.{action}", name=f"{action} materiality",
                module_code="materiality", action=action.upper(),
            )
            role.permissions.add(permission)
        UserRoleAssignment.objects.create(user=self.user, role=role, module_code="materiality")
        self.client.force_authenticate(self.user)

    def test_anonymous_group_link_creates_independent_submissions_and_scores_only_submitted(self):
        link = SurveyGroupLink.objects.create(survey=self.survey, stakeholder_group=self.group)
        initial = self.client.get(f"/api/public/materiality/survey/{link.token}/")
        draft_token = initial.data["response_token"]
        self.client.post(f"/api/public/materiality/survey/{link.token}/answer/", {"response_token": draft_token, "question": str(self.impact_question.id), "value": 1}, format="json")
        self._answer_and_submit(link.token, value=4)
        self._answer_and_submit(link.token, value=5)
        self.assertEqual(SurveySubmission.objects.filter(source="ANONYMOUS", submitted_at__isnull=False).count(), 2)
        self._grant_materiality_access("view")
        group_links = self.client.get(
            f"/api/materiality/assessments/{self.assessment.id}/survey/group-links/"
        )
        self.assertEqual(group_links.status_code, 200)
        self.assertEqual(group_links.data[0]["anonymous_submitted_count"], 2)
        run = run_scoring(self.assessment, self.user)
        result = run.topic_results.get()
        self.assertEqual(result.primary_score, Decimal("4.50"))
        self.assertEqual(result.secondary_score, Decimal("4.50"))
        self.assertEqual(run.response_count, 2)

    def test_identified_invitation_is_tracked(self):
        stakeholder = Stakeholder.objects.create(group=self.group, name="Known", email="known@example.test")
        invitation = SurveyInvitation.objects.create(survey=self.survey, stakeholder=stakeholder)
        self._answer_and_submit(invitation.token, value=3)
        self.assertEqual(invitation.submission.source, "IDENTIFIED")
        self.assertEqual(invitation.submission.stakeholder_group, self.group)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "SUBMITTED")
        self.assertEqual(SurveyResponse.objects.filter(submission=invitation.submission).count(), 2)

    def test_public_links_resume_one_submission_and_become_read_only_after_submit(self):
        group_link = SurveyGroupLink.objects.create(survey=self.survey, stakeholder_group=self.group)
        response_token = self._answer_and_submit(group_link.token, value=4)
        resumed = self.client.get(
            f"/api/public/materiality/survey/{group_link.token}/",
            {"response_token": response_token},
        )
        self.assertEqual(resumed.status_code, 200)
        self.assertTrue(resumed.data["submitted"])
        self.assertEqual(
            self.client.post(
                f"/api/public/materiality/survey/{group_link.token}/answer/",
                {"response_token": response_token, "question": str(self.impact_question.id), "value": 2},
                format="json",
            ).status_code,
            400,
        )

        stakeholder = Stakeholder.objects.create(group=self.group, name="Known", email="known@example.test")
        invitation = SurveyInvitation.objects.create(survey=self.survey, stakeholder=stakeholder)
        self._answer_and_submit(invitation.token, value=3)
        invitation_view = self.client.get(f"/api/public/materiality/survey/{invitation.token}/")
        self.assertEqual(invitation_view.status_code, 200)
        self.assertTrue(invitation_view.data["submitted"])

    def test_stakeholder_edit_delete_template_and_locked_read_access(self):
        self._grant_materiality_access("view", "manage")
        base = f"/api/materiality/assessments/{self.assessment.id}"
        created = self.client.post(
            f"{base}/stakeholders/",
            {"group": str(self.group.id), "name": "Editable", "email": "edit@example.test"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        stakeholder_id = created.data["id"]
        updated = self.client.patch(
            f"{base}/stakeholders/{stakeholder_id}/",
            {"designation": "Director"}, format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["designation"], "Director")
        self.assertEqual(self.client.delete(f"{base}/stakeholders/{stakeholder_id}/").status_code, 204)

        prepared = self.client.post(f"{base}/survey/prepare-distribution/")
        self.assertEqual(prepared.status_code, 200)
        self.assertEqual(prepared.data["group_link_count"], 1)
        self.assertEqual(prepared.data["invitation_count"], 0)

        template = self.client.get(f"{base}/stakeholder-import-template/")
        self.assertEqual(template.status_code, 200)
        self.assertIn(b"group,name,email,organisation,designation", template.content)
        upload = SimpleUploadedFile(
            "stakeholders.csv",
            f"# comment\ngroup,name,email,organisation,designation\n{self.group.id},Imported,imported@example.test,Example,Analyst\n".encode(),
            content_type="text/csv",
        )
        imported = self.client.post(f"{base}/stakeholders/import/", {"file": upload}, format="multipart")
        self.assertEqual(imported.status_code, 201)
        imported_stakeholder = Stakeholder.objects.get(email="imported@example.test")
        invitation = SurveyInvitation.objects.get(survey=self.survey, stakeholder=imported_stakeholder)
        invitation.sent_at = self.survey.created_at
        invitation.status = "SENT"
        invitation.save(update_fields=["sent_at", "status"])
        self.assertEqual(self.client.delete(f"{base}/stakeholders/{imported_stakeholder.id}/").status_code, 400)

        self.assessment.is_locked = True
        self.assessment.save(update_fields=["is_locked"])
        self.assertEqual(self.client.get(f"{base}/groups/").status_code, 200)
        self.assertEqual(self.client.get(f"{base}/stakeholders/").status_code, 200)
        self.assertEqual(self.client.get(f"{base}/survey/").status_code, 200)
        self.assertEqual(self.client.post(
            f"{base}/stakeholders/",
            {"group": str(self.group.id), "name": "Blocked", "email": "blocked@example.test"},
            format="json",
        ).status_code, 400)

    def test_draft_and_closed_surveys_are_not_publicly_accessible(self):
        link = SurveyGroupLink.objects.create(survey=self.survey, stakeholder_group=self.group)
        self.survey.status = "READY"
        self.survey.save(update_fields=["status"])
        self.assertEqual(self.client.get(f"/api/public/materiality/survey/{link.token}/").status_code, 404)
        self.survey.status = "CLOSED"
        self.survey.save(update_fields=["status"])
        self.assertEqual(self.client.get(f"/api/public/materiality/survey/{link.token}/").status_code, 404)

    def test_no_submitted_group_data_is_preserved_as_insufficient_not_zero(self):
        run = run_scoring(self.assessment, self.user)
        result = run.topic_results.get()
        self.assertIsNone(result.primary_score)
        self.assertIsNone(result.secondary_score)
        self.assertEqual(result.classification, "INSUFFICIENT_DATA")

    def test_override_is_captured_in_the_score_run_history(self):
        self.assessment_topic.is_override = True
        self.assessment_topic.classification = "MATERIAL"
        self.assessment_topic.override_reason = "Evidence and governance review justify this classification."
        self.assessment_topic.save()
        run = run_scoring(self.assessment, self.user)
        historical = run.topic_results.get()
        self.assertTrue(historical.is_override)
        self.assertEqual(historical.override_reason, self.assessment_topic.override_reason)
        self.assessment_topic.override_reason = "A later change must not rewrite the historical score run."
        self.assessment_topic.save()
        historical.refresh_from_db()
        self.assertNotEqual(historical.override_reason, self.assessment_topic.override_reason)

    def test_double_materiality_blends_submitted_stakeholder_and_internal_scores(self):
        self.assessment.mode = "DOUBLE"
        self.assessment.internal_blend_weight = Decimal("0.50")
        self.assessment.save()
        self.importance_question.is_required = False
        self.importance_question.save(update_fields=["is_required"])
        financial_scale = ScaleDefinition.objects.create(dimension="FINANCIAL", name="Financial")
        for value in range(1, 6):
            ScaleOption.objects.create(scale=financial_scale, value=value, label=str(value))
        financial_question = SurveyQuestion.objects.create(survey=self.survey, assessment_topic=self.assessment_topic, scale=financial_scale, dimension="FINANCIAL", question_text="Financial?", display_order=3)
        link = SurveyGroupLink.objects.create(survey=self.survey, stakeholder_group=self.group)
        initial = self.client.get(f"/api/public/materiality/survey/{link.token}/")
        token = initial.data["response_token"]
        for question in (self.impact_question, financial_question):
            self.client.post(f"/api/public/materiality/survey/{link.token}/answer/", {"response_token": token, "question": str(question.id), "value": 4}, format="json")
        self.client.post(f"/api/public/materiality/survey/{link.token}/submit/", {"response_token": token}, format="json")
        InternalScore.objects.create(assessment_topic=self.assessment_topic, impact_type="ACTUAL", scale=2, scope=2, irremediability=2, financial_magnitude=2, financial_likelihood=2, scored_by=self.user)
        result = run_scoring(self.assessment, self.user).topic_results.get()
        self.assertEqual(result.primary_score, Decimal("3.00"))
        self.assertEqual(result.secondary_score, Decimal("2.40"))

    def test_internal_assessment_api_requires_the_canonical_materiality_permission(self):
        self.client.force_authenticate(self.user)
        url = "/api/materiality/assessments/"
        self.assertEqual(self.client.get(url).status_code, 403)
        permission = Permission.objects.create(code="materiality.view", name="View materiality", module_code="materiality", action="VIEW")
        role = Role.objects.create(role_code="materiality_viewer", role_name="Materiality viewer")
        role.permissions.add(permission)
        assignment = UserRoleAssignment.objects.create(user=self.user, role=role, module_code="materiality")
        self.assertEqual(self.client.get(url).status_code, 200)
        root = OrgNode.objects.get(company=self.company, node_type="LEGAL_ENTITY", parent__isnull=True)
        assignment.org_node = root
        assignment.save()
        self.assertEqual(self.client.get(url).status_code, 200)
        node = OrgNode.objects.create(
            company=self.company, parent=root, node_type="FACILITY", code="SITE", name="Site",
            facility_type="Test facility",
        )
        assignment.org_node = node
        assignment.save()
        self.assertEqual(self.client.get(url).status_code, 403)


class DemoMaterialitySeedTests(TestCase):
    def test_seed_demo_materiality_is_idempotent_and_creates_three_visual_states(self):
        owner = User.objects.create_superuser(username="demo-owner", password="test-pass")

        call_command("seed_demo_materiality", owner=owner.username, verbosity=0)
        assessment = MaterialityAssessment.objects.get(name="Demo — FY 2025-26 Materiality Assessment")
        call_command("seed_demo_materiality", owner=owner.username, verbosity=0)

        assessment.refresh_from_db()
        self.assertEqual(assessment.mode, "DOUBLE")
        self.assertEqual(assessment.status, "IN_PROGRESS")
        self.assertEqual(assessment.stakeholder_groups.count(), 6)
        self.assertEqual(assessment.assessment_topics.filter(is_included=True).count(), 10)
        self.assertEqual(Stakeholder.objects.filter(group__assessment=assessment).count(), 18)
        survey = Survey.objects.get(assessment=assessment)
        self.assertEqual(survey.status, "READY")
        self.assertEqual(survey.invitations.count(), 18)
        self.assertEqual(survey.group_links.count(), 6)
        self.assertFalse(ScoreRun.objects.filter(assessment=assessment).exists())
        self.assertFalse(InternalScore.objects.filter(assessment_topic__assessment=assessment).exists())
        self.assertFalse(assessment.assessment_topics.filter(is_override=True).exists())

        draft = MaterialityAssessment.objects.get(name="Demo — Draft Materiality Assessment")
        self.assertEqual(draft.status, "DRAFT")
        self.assertFalse(draft.assessment_topics.exists())

        completed = MaterialityAssessment.objects.get(name="Demo — Completed Materiality Assessment")
        self.assertEqual(completed.status, "COMPLETED")
        self.assertTrue(completed.is_locked)
        self.assertEqual(completed.score_runs.count(), 1)
        completed_survey = Survey.objects.get(assessment=completed)
        self.assertEqual(completed_survey.group_links.count(), 6)
        self.assertEqual(
            SurveySubmission.objects.filter(
                survey=completed_survey,
                submitted_at__isnull=False,
            ).count(),
            18,
        )
        self.assertSetEqual(
            set(completed.assessment_topics.values_list("classification", flat=True)),
            {
                "DOUBLE_MATERIAL",
                "IMPACT_MATERIAL",
                "FINANCIAL_MATERIAL",
                "NOT_MATERIAL",
            },
        )
        self.assertTrue(completed.assessment_topics.filter(is_override=True).exists())

    def test_seed_does_not_mix_with_an_existing_non_demo_assessment(self):
        owner = User.objects.create_superuser(username="demo-owner", password="test-pass")
        company = Company.objects.create(
            company_name="Existing Co", company_code="EXISTING", contact_person="Owner",
            email="owner@example.test", mobile_number="1234567890",
        )
        period = ReportingPeriod.objects.create(
            name="Existing FY 2025-26", period_type="ANNUAL",
            start_date=date(2025, 4, 1), end_date=date(2026, 3, 31),
        )
        existing = MaterialityAssessment.objects.create(
            company=company, reporting_period=period,
            name="FY 2025-26 Materiality Assessment", created_by=owner,
        )
        StakeholderGroup.objects.create(assessment=existing, name="Legacy group", weight=Decimal("155"))

        call_command("seed_demo_materiality", owner=owner.username, verbosity=0)

        existing.refresh_from_db()
        self.assertEqual(existing.stakeholder_groups.get().weight, Decimal("155"))
        self.assertTrue(MaterialityAssessment.objects.filter(
            name="Demo — FY 2025-26 Materiality Assessment"
        ).exists())
