from django import template

register = template.Library()

@register.filter(name='split')
def split(value, key):
    return value.split(key)

@register.filter(name='get_option')
def get_option(question, answer):
    options = {
        1: question.option1,
        2: question.option2,
        3: question.option3,
        4: question.option4,
    }
    return options.get(answer, '')


@register.filter(name='is_teacher')
def is_teacher(user):
    return hasattr(user, 'profile') and user.profile.is_teacher


@register.filter
def is_pdf(file_url):
    return file_url.lower().endswith('.pdf')

@register.filter
def is_doc(file_url):
    return file_url.lower().endswith('.doc') or file_url.lower().endswith('.docx')