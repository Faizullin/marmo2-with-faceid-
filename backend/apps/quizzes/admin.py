from django.contrib import admin

from .models import Question, QuestionAttempt, QuizResult, Lecture, LecturePage, LectureTestPage, LectureResult, \
    TestResult, AppliedCourse, Course, CourseSurvey

admin.site.register(Question)
admin.site.register(QuestionAttempt)
admin.site.register(QuizResult)
admin.site.register(AppliedCourse)
admin.site.register(Lecture)
admin.site.register(LecturePage)
admin.site.register(LectureTestPage)
admin.site.register(LectureResult)
admin.site.register(TestResult)
admin.site.register(Course)
admin.site.register(CourseSurvey)