from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.urls import reverse

class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.score}/{self.total_questions} on {self.date_taken}"
        


class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='courses/', default='courses/default.jpg')
    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class AppliedCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} applied to {self.course.name}"

class CourseSurvey(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='surveys')
    survey_link = models.URLField(max_length=200, help_text="Осы курстың сауалнамасына сілтеме")

class Lecture(models.Model):
    course = models.ForeignKey(Course, related_name='lectures', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    lecture_number = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.pk:
            last_lecture = Lecture.objects.filter(course=self.course).order_by('lecture_number').last()
            if last_lecture:
                self.lecture_number = last_lecture.lecture_number + 1
            else:
                self.lecture_number = 1
        super(Lecture, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

class LecturePage(models.Model):
    lecture = models.ForeignKey(Lecture, related_name='pages', on_delete=models.CASCADE)
    page_number = models.IntegerField()
    content = models.TextField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='lecture_images/', blank=True, null=True)
    files = models.FileField(upload_to='lecture_files/', blank=True, null=True)
    max_attempts = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk:
            # Ensure the page number logic is only run for new instances
            existing_page_numbers = self.lecture.pages.values_list('page_number', flat=True)
            next_page_number = 1
            while next_page_number in existing_page_numbers:
                next_page_number += 1
            self.page_number = next_page_number
        super(LecturePage, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.lecture.title} - Page {self.page_number}"

    def get_absolute_url(self):
        return reverse('edit_lecture_page', kwargs={'course_id': self.lecture.course.id, 'lecture_id': self.lecture.id, 'page_number': self.page_number})


class QuizResult(models.Model):
    user = models.ForeignKey(User, related_name='quiz_results', on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, related_name='quiz_lecture_results', on_delete=models.CASCADE)
    score = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.lecture.title} - {self.score}"



class LectureTestPage(models.Model):
    lecture = models.OneToOneField(Lecture, related_name='test_page', on_delete=models.CASCADE)

    def __str__(self):
        return f"Test for {self.lecture.title}"




def get_default_test_page():
    try:
        latest_lecture = Lecture.objects.latest('id')
        test_page, created = LectureTestPage.objects.get_or_create(lecture=latest_lecture)
        return test_page
    except ObjectDoesNotExist:
        return None  # or handle this case differently if needed


#class Question(models.Model):
#    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
#    text = models.CharField(max_length=255)
#    options = models.JSONField()  # or use a separate model for options
#    correct_option = models.CharField(max_length=255)

class Question(models.Model):
    test_page = models.ForeignKey(LectureTestPage, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    correct_option = models.IntegerField()

    def __str__(self):
        return self.text

class Option(models.Model):
    question = models.ForeignKey(Question, related_name='question_options', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)


class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=255)
    is_correct = models.BooleanField()

    class Meta:
        unique_together = ('user', 'question')

class UserLectureAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    attempts = models.IntegerField(default=3)
    completed_attempts = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)  # Track if lecture is completed

    def can_attempt(self):
        return self.completed_attempts <= self.attempts

class LectureCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    score = models.FloatField()




#outdated

class QuestionAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='attempts', on_delete=models.CASCADE)
    selected_option = models.IntegerField()
    is_correct = models.BooleanField()
    attempt_number = models.PositiveIntegerField()

class LectureResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, related_name='results', on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.lecture.title} - {self.score}/{self.total_questions}"



