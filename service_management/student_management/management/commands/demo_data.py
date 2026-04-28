import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from student_management.models import School, Classroom, Teacher, Parent, Student, RFIDCard
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Generate demo data: students, teachers, classrooms, parents, RFIDs only.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting focused demo data creation...'))
        User = get_user_model()

        schools = [School.objects.create(name=f'School {i}', slug=f'school-{i}') for i in range(1, 2)]

        classrooms = []
        for school in schools:
            for grade in range(1, 13):
                for section in ['A', 'B']:
                    classrooms.append(Classroom.objects.create(
                        school=school, grade=grade, section=section, room_number=f'{grade}{section}'
                    ))

        teachers = []
        for school in schools:
            for i in range(1, 11):
                user = User.objects.create_user(
                    email=f'teacher{i}@{school.slug}.com',
                    password='password',
                    school=school,
                    role='Teacher',
                    first_name=f'Teacher{i}',
                    last_name=f'Lastname{i}'
                )
                teachers.append(Teacher.objects.create(
                    school=school,
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    subject_specialization=random.choice(['Math', 'Science', 'English', 'History']),
                    is_active=True
                ))

        parents = []
        for school in schools:
            for i in range(1, 21):
                user = User.objects.create_user(
                    email=f'parent{i}@{school.slug}.com',
                    password='password',
                    school=school,
                    role='Parent',
                    first_name=f'Parent{i}',
                    last_name=f'Lastname{i}'
                )
                parents.append(Parent.objects.create(
                    school=school,
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    relation=random.choice(['MOTHER', 'FATHER', 'GUARDIAN'])
                ))

        students = []
        for school in schools:
            for i in range(1, 51):
                user = User.objects.create_user(
                    email=f'student{i}@{school.slug}.com',
                    password='password',
                    school=school,
                    role='Student',
                    first_name=f'Student{i}',
                    last_name=f'Lastname{i}'
                )
                classroom = random.choice(classrooms)
                parent = random.choice(parents)
                students.append(Student.objects.create(
                    school=school,
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    dob=timezone.now().date(),
                    roll_number=i,
                    is_fully_enrolled=True,
                    classroom=classroom,
                    parent=parent,
                    gender=random.choice(['M', 'F', 'O']),
                    admission_number=f'ADM{i}{school.slug}',
                    is_active=True
                ))

        for student in students:
            RFIDCard.objects.create(
                school=student.school,
                uid=f'RFID{student.roll_number}{student.school.slug}',
                assigned_to_student=student,
                status='ACTIVE'
            )

        self.stdout.write(self.style.SUCCESS('Demo data created: students, teachers, classrooms, parents, RFIDs.'))
