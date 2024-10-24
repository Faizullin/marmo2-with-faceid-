from django import forms
from .models import Course, Lecture, LecturePage, Question, Option, LectureTestPage, CourseSurvey
from django.utils.translation import gettext_lazy as _



class LecturePageForm(forms.ModelForm):
    class Meta:
        model = LecturePage
        fields = ['content', 'video_url', 'image', 'files']
        labels = {
            'content': 'Мазмұны',
            'video_url': 'Видеоның URL-ы',
            'image': 'Бейне',
            'files': 'Файлдар',
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'option1', 'option2', 'option3', 'option4', 'correct_option']
        labels = {
            'text': 'Сұрақ мәтіні',
            'option1': '1 нұсқа',
            'option2': '2 нұсқа',
            'option3': '3 нұсқа',
            'option4': '4 нұсқа',
            'correct_option': 'Дұрыс нұсқа',
        }

    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        options = [
            (1, '1 нұсқа'),
            (2, '2 нұсқа'),
            (3, '3 нұсқа'),
            (4, '4 нұсқа'),
        ]
        self.fields['correct_option'] = forms.ChoiceField(choices=options, label='Дұрыс нұсқа')


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['text', 'is_correct']
        labels = {
            'text': 'Текст варианта',
            'is_correct': 'Правильный вариант',
        }




class CustomClearableFileInput(forms.ClearableFileInput):
    template_name = 'widgets/custom_clearable_file_input.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({'class': 'custom-file-input'})

    def format_value(self, value):
        # Override this method to change the initial text if needed
        return super().format_value(value)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'description', 'image']
        labels = {
            'name': 'Курстың атауы',
            'description': 'Курстың сипаттамасы',
            'image': 'Курстың суреті',
        }
        widgets = {
            'image': CustomClearableFileInput(attrs={'placeholder': 'Файлды таңдаңыз'}),
        }

class LectureForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = ['title', 'description']
        labels = {
            'title': 'Дәрістің атауы',
            'description': 'Дәрістің сипаттамасы',
        }


class LectureTestPageForm(forms.ModelForm):
    class Meta:
        model = LectureTestPage
        fields = []  # No direct fields for the test page itself


class SurveyForm(forms.ModelForm):
    class Meta:
        model = CourseSurvey
        fields = ['survey_link']
        labels = {
            'survey_link': 'Сауалнаманың сілтемесі'
        }
        widgets = {
            'survey_link': forms.URLInput(attrs={'class': 'form-control'})
        }