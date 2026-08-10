from django.core.management.base import BaseCommand
from django.db import transaction

from apps.materiality.models import (
    TopicCategory,
    MaterialTopic,
    MaterialSubTopic,
)


class Command(BaseCommand):
    help = "Seed default ESG materiality topic library"

    def handle(self, *args, **options):

        with transaction.atomic():

            # =========================================================
            # CATEGORIES
            # =========================================================

            categories = {}

            category_data = [
                {
                    "code": "E",
                    "name": "Environmental",
                    "display_order": 1,
                },
                {
                    "code": "S",
                    "name": "Social",
                    "display_order": 2,
                },
                {
                    "code": "G",
                    "name": "Governance",
                    "display_order": 3,
                },
            ]

            for data in category_data:
                category, _ = TopicCategory.objects.get_or_create(
                    code=data["code"],
                    defaults={
                        "name": data["name"],
                        "display_order": data["display_order"],
                    },
                )

                categories[data["code"]] = category

            # =========================================================
            # TOPICS
            # =========================================================

            topics = [
                {
                    "category": categories["E"],
                    "name": "Climate Change",
                    "description": (
                        "Climate change impacts, greenhouse gas emissions, "
                        "climate-related risks and opportunities, and the "
                        "organization's transition towards a low-carbon economy."
                    ),
                    "display_order": 1,
                    "subtopics": [
                        {
                            "name": "Greenhouse Gas Emissions",
                            "description": (
                                "Management and reduction of Scope 1, Scope 2 "
                                "and relevant Scope 3 greenhouse gas emissions."
                            ),
                            "display_order": 1,
                        },
                        {
                            "name": "Climate Risks and Opportunities",
                            "description": (
                                "Identification and management of physical and "
                                "transition risks and opportunities arising "
                                "from climate change."
                            ),
                            "display_order": 2,
                        },
                        {
                            "name": "Climate Transition Strategy",
                            "description": (
                                "Plans, targets and actions for reducing "
                                "emissions and transitioning towards a "
                                "lower-carbon business model."
                            ),
                            "display_order": 3,
                        },
                    ],
                },
                {
                    "category": categories["E"],
                    "name": "Resource Use & Circular Economy",
                    "description": (
                        "Responsible use of natural resources, waste generation, "
                        "resource efficiency and transition towards circular "
                        "production and consumption models."
                    ),
                    "display_order": 2,
                    "subtopics": [
                        {
                            "name": "Resource Consumption",
                            "description": (
                                "Use and efficiency of materials, raw materials "
                                "and other natural resources."
                            ),
                            "display_order": 1,
                        },
                        {
                            "name": "Waste Management",
                            "description": (
                                "Waste generation, segregation, treatment, "
                                "recycling, reuse and responsible disposal."
                            ),
                            "display_order": 2,
                        },
                        {
                            "name": "Circular Economy",
                            "description": (
                                "Actions to reduce resource consumption through "
                                "reuse, recycling, recovery, product life "
                                "extension and circular business practices."
                            ),
                            "display_order": 3,
                        },
                    ],
                },
                {
                    "category": categories["S"],
                    "name": "Occupational Health & Safety",
                    "description": (
                        "Protection of workers from workplace health and safety "
                        "risks and promotion of safe and healthy working conditions."
                    ),
                    "display_order": 1,
                    "subtopics": [
                        {
                            "name": "Workplace Health & Safety",
                            "description": (
                                "Identification, prevention and control of "
                                "occupational health and safety hazards."
                            ),
                            "display_order": 1,
                        },
                        {
                            "name": "Workplace Incidents and Injuries",
                            "description": (
                                "Prevention and management of workplace "
                                "incidents, injuries, fatalities and "
                                "occupational illnesses."
                            ),
                            "display_order": 2,
                        },
                        {
                            "name": "Safety Training and Awareness",
                            "description": (
                                "Employee training, safety awareness programs, "
                                "emergency preparedness and safety culture."
                            ),
                            "display_order": 3,
                        },
                    ],
                },
                {
                    "category": categories["S"],
                    "name": "Human Capital & Labor Practices",
                    "description": (
                        "Employee development, fair employment practices, "
                        "workforce wellbeing, diversity and responsible "
                        "management of human capital."
                    ),
                    "display_order": 2,
                    "subtopics": [
                        {
                            "name": "Employee Development",
                            "description": (
                                "Training, skill development, career growth "
                                "and learning opportunities for employees."
                            ),
                            "display_order": 1,
                        },
                        {
                            "name": "Diversity, Equity & Inclusion",
                            "description": (
                                "Workforce diversity, equal opportunity, "
                                "inclusion and prevention of discrimination."
                            ),
                            "display_order": 2,
                        },
                        {
                            "name": "Employee Wellbeing",
                            "description": (
                                "Employee wellbeing, work-life balance, "
                                "engagement and supportive workplace practices."
                            ),
                            "display_order": 3,
                        },
                    ],
                },
                {
                    "category": categories["G"],
                    "name": "Business Ethics & Anti-Corruption",
                    "description": (
                        "Ethical business conduct, prevention of corruption "
                        "and bribery, responsible decision-making and mechanisms "
                        "for reporting and addressing unethical conduct."
                    ),
                    "display_order": 1,
                    "subtopics": [
                        {
                            "name": "Anti-Corruption and Bribery",
                            "description": (
                                "Policies, controls, training and actions to "
                                "prevent bribery and corruption."
                            ),
                            "display_order": 1,
                        },
                        {
                            "name": "Ethical Business Conduct",
                            "description": (
                                "Standards of ethical conduct, code of conduct, "
                                "conflicts of interest and responsible business "
                                "decision-making."
                            ),
                            "display_order": 2,
                        },
                        {
                            "name": "Whistleblower and Grievance Mechanisms",
                            "description": (
                                "Confidential channels for reporting concerns, "
                                "protection against retaliation and processes "
                                "for investigating reported misconduct."
                            ),
                            "display_order": 3,
                        },
                    ],
                },
            ]

            # =========================================================
            # CREATE TOPICS + SUBTOPICS
            # =========================================================

            for topic_data in topics:

                topic, _ = MaterialTopic.objects.get_or_create(
                    category=topic_data["category"],
                    company=None,
                    name=topic_data["name"],
                    defaults={
                        "description": topic_data["description"],
                        "display_order": topic_data["display_order"],
                        "is_active": True,
                    },
                )

                for subtopic_data in topic_data["subtopics"]:

                    MaterialSubTopic.objects.get_or_create(
                        topic=topic,
                        name=subtopic_data["name"],
                        defaults={
                            "description": subtopic_data["description"],
                            "display_order": subtopic_data["display_order"],
                            "is_active": True,
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Materiality topic library seeded successfully."
            )
        )