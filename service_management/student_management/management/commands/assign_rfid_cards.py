from django.core.management.base import BaseCommand
from django.db import transaction
from student_management.models import Student, RFIDCard, School
from core.services.student_service import StudentService
from core.services.exceptions import DuplicateEntryError
import csv


class Command(BaseCommand):
    help = 'Bulk assign RFID cards to students from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            help='Path to CSV file (columns: admission_number, rfid_uid)'
        )
        parser.add_argument(
            '--school-id',
            type=int,
            required=True,
            help='School ID'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        school_id = options['school_id']
        csv_path = options.get('csv')

        try:
            school = School.objects.get(pk=school_id)
        except School.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'School {school_id} not found'))
            return

        if csv_path:
            success_count = 0
            error_count = 0
            
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    admission_number = row.get('admission_number')
                    rfid_uid = row.get('rfid_uid')
                    
                    try:
                        student = Student.objects.get(
                            school=school,
                            admission_number=admission_number
                        )
                        StudentService.assign_rfid_card_to_student(student.pk, rfid_uid)
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ {student.last_name} ({admission_number}) → {rfid_uid}'
                            )
                        )
                    except Student.DoesNotExist:
                        error_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠️ Student with admission {admission_number} not found'
                            )
                        )
                    except DuplicateEntryError as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'❌ {str(e)}')
                        )
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'❌ Error processing {admission_number}: {str(e)}')
                        )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Successfully assigned: {success_count} | Errors: {error_count}'
                )
            )
        else:
            self.stdout.write('No CSV file provided. Use --csv option.')
