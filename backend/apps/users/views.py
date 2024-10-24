import base64
import io

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_backends, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.views import View

from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm, CustomAuthenticationForm
from .models import Profile, OneTimeToken


# class CustomLoginView(LoginView):
#    form_class = CustomAuthenticationForm
class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'users/login.html'


def home(request):
    return render(request, 'users/home.html')


# class RegisterView(View):
#    form_class = RegisterForm
#    initial = {'key': 'value'}
#    template_name = 'users/register.html'
#
#    def dispatch(self, request, *args, **kwargs):
#        if request.user.is_authenticated:
#            return redirect(to='/')
#        return super(RegisterView, self).dispatch(request, *args, **kwargs)
#
#    def get(self, request, *args, **kwargs):
#        form = self.form_class(initial=self.initial)
#        return render(request, self.template_name, {'form': form})
#
#    def post(self, request, *args, **kwargs):
#        form = self.form_class(request.POST)
#        if form.is_valid():
#            form.save()
#            username = form.cleaned_data.get('username')
#            messages.success(request, _('Аккаунт создан для %(username)s') % {'username': username})
#            return redirect(to='login')
#        return render(request, self.template_name, {'form': form})
class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(to='/')
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            # Profile.objects.create(user=user)  # Remove this line
            username = form.cleaned_data.get('username')
            messages.success(request, _('Аккаунт создан для %(username)s') % {'username': username})
            return redirect(to='login')
        else:
            messages.error(request, 'Исправьте ошибки в форме.')
        return render(request, self.template_name, {'form': form})


# Классовое представление, расширяющее встроенное представление входа для добавления функциональности "Запомнить меня"
# class CustomLoginView(LoginView):
#    template_name = 'users/login.html'
#    form_class = LoginForm
#    redirect_authenticated_user = True
#
#    def get(self, request, *args, **kwargs):
#        print("CustomLoginView accessed")
#        return super().get(request, *args, **kwargs)
#        
#    def form_valid(self, form):
#        remember_me = form.cleaned_data.get('remember_me')
#
#        if not remember_me:
#            # установить срок действия сессии на 0 секунд. Таким образом, сессия автоматически закроется после закрытия браузера.
#            self.request.session.set_expiry(0)
#
#            # Установить сессию как измененную для принудительного обновления данных/сохранения куки.
#            self.request.session.modified = True
#
#        # иначе сеанс браузера будет длиться столько, сколько указано в "SESSION_COOKIE_AGE" в settings.py
#        return super(CustomLoginView, self).form_valid(form)
#
#    def form_invalid(self, form):
#        messages.error(self.request, 'Неправильный логин или пароль')
#        return super(CustomLoginView, self).form_invalid(form)


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        print("CustomLoginView accessed")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        # Ensure the user has a profile
        profile, created = Profile.objects.get_or_create(user=user)

        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # Set the session to expire at browser close
            self.request.session.set_expiry(0)
            self.request.session.modified = True

        return super(CustomLoginView, self).form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Неправильный логин или пароль')
        return super(CustomLoginView, self).form_invalid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject'
    success_message = _(
        "Мы отправили вам инструкции по установке пароля, "
        "если учетная запись существует с введенным вами email. Вы получите их в ближайшее время."
        " Если вы не получили письмо, "
        "пожалуйста, убедитесь, что вы ввели адрес, с которым вы регистрировались, и проверьте папку со спамом."
    )
    success_url = reverse_lazy('users-home')


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    success_message = _("Пароль успешно изменен")
    success_url = reverse_lazy('users-home')


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'users/login.html'


# @login_required
# def profile(request):
#    if request.method == 'POST':
#        user_form = UpdateUserForm(request.POST, instance=request.user)
#        profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)
#
#        if user_form.is_valid() and profile_form.is_valid():
#            user_form.save()
#            profile_form.save()
#            messages.success(request, _('Ваш профиль успешно обновлен'))
#            return redirect(to='users-profile')
#    else:
#        user_form = UpdateUserForm(instance=request.user)
#        profile_form = UpdateProfileForm(instance=request.user.profile)
#
#    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_form': profile_form})

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _('Ваш профиль успешно обновлен'))
            return redirect(to='users-profile')
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }

    return render(request, 'users/profile.html', context)


def send_qr_code(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            token = get_random_string(32)
            OneTimeToken.objects.create(user=user, token=token)

            qr_code_url = request.build_absolute_uri(reverse('qr_login', args=[token]))
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_code_url)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # Send email with QR code
            email_content = f"""
                <p>Please use the attached QR code or click the link below to log in to your account.</p>
                <img src="data:image/png;base64,{img_str}"/><br>
                <a href="{qr_code_url}">Зайти в аккаунт</a>
            """
            send_mail(
                'Your QR Code Login',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=email_content
            )

            messages.success(request, _('Письмо с QR кодом отправлено на вашу почту'))
            return redirect('users-home')
        except User.DoesNotExist:
            messages.error(request, _('Пользователь с таким email не найден.'))
            return redirect('users-home')
    else:
        return HttpResponse('Invalid request method.')


def qr_login(request, token):
    try:
        one_time_token = OneTimeToken.objects.get(token=token, is_used=False)
        if one_time_token.is_valid():
            one_time_token.is_used = True
            one_time_token.save()

            # Get the user's backend
            backend = get_backends()[0]  # Using the first backend as an example, modify if needed
            user = one_time_token.user
            user.backend = f'{backend.__module__}.{backend.__class__.__name__}'

            login(request, user)
            return redirect('users-home')
        else:
            return HttpResponse('Token is invalid or expired.')
    except OneTimeToken.DoesNotExist:
        return HttpResponse('Invalid token.')


def logout_view(request):
    logout(request)
    return redirect("/")
