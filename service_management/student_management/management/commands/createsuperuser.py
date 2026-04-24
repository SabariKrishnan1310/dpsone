from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand
from student_management.models import School


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.UserModel.REQUIRED_FIELDS = []

        school, _ = School.objects.get_or_create(
            slug='default-school',
            defaults={'name': 'Default School', 'is_active': True}
        )

        options['school'] = school

        super().handle(*args, **options)
