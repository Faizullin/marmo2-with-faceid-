from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Profile


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100,
                                 required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'Аты',
                                                               'class': 'form-control',
                                                               }),
                                 )
    last_name = forms.CharField(max_length=100,
                                required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Тегі',
                                                              'class': 'form-control',
                                                              }))
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Пайдаланушы аты',
                                                             'class': 'form-control',
                                                             }))
    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Электрондық пошта',
                                                           'class': 'form-control',
                                                           }))
    password1 = forms.CharField(max_length=50,
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Құпия сөз',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  'id': 'password',
                                                                  }))
    password2 = forms.CharField(max_length=50,
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Құпия сөзді растаңыз',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  'id': 'password',
                                                                  }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']
        

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Пользователь с таким именем уже существует.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email


class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': _(
            "Пожалуйста, введите правильное имя пользователя и пароль. "
            "Учтите, что оба поля чувствительны к регистру."
        ),
        'inactive': _("Этот аккаунт неактивен."),
    }


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Пайдаланушы аты',
                                                             'class': 'form-control',
                                                             }))
    password = forms.CharField(max_length=50,
                               required=True,
                               widget=forms.PasswordInput(attrs={'placeholder': 'Құпия сөз',
                                                                 'class': 'form-control',
                                                                 'data-toggle': 'password',
                                                                 'id': 'password',
                                                                 'name': 'password',
                                                                 }))
    remember_me = forms.BooleanField(required=False, label='Запомнить меня')


    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class UpdateUserForm(forms.ModelForm):
    username = forms.CharField(
        max_length=100,
        required=True,
        label='Қолданушы аты',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Қолданушы аты'
        })
    )
    email = forms.EmailField(
        required=True,
        label='Электрондық пошта',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Электрондық пошта'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {
            'username': 'Қолданушы аты',
            'email': 'Электрондық пошта'
        }


class UpdateProfileForm(forms.ModelForm):
    avatar = forms.ImageField(
        label='Аватар',
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'placeholder': 'Аватар'
        })
    )
    bio = forms.CharField(
        label='Биография',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Биография'
        })
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'bio']
        labels = {
            'avatar': 'Аватар',
            'bio': 'Биография'
        }