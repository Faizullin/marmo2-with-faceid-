from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory
from .models import TestResult, Question, Option, QuizResult, Course, AppliedCourse, Lecture, LecturePage, LectureTestPage, Answer, LecturePage, CourseSurvey, UserLectureAttempt, LectureCompletion
from .forms import QuestionForm, CourseForm, LectureForm, LecturePageForm, LectureTestPageForm, SurveyForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, FileResponse, Http404
from django.contrib import messages
from django.db.models import *

@login_required
def quiz_view(request):
    if request.method == 'POST':
        score = request.POST.get('score')
        total_questions = request.POST.get('total_questions')

        TestResult.objects.create(
            user=request.user,
            score=score,
            total_questions=total_questions
        )

        return redirect('quiz_history')

    return render(request, 'quizzes/quiz.html')

@login_required
def quiz_history_view(request):
    test_results = TestResult.objects.filter(user=request.user).order_by('-date_taken')
    return render(request, 'quizzes/quiz_history.html', {'test_results': test_results})


@login_required
def profile_view(request):
    quiz_results = QuizResult.objects.filter(user=request.user)
    return render(request, 'users/profile.html', {'quiz_results': quiz_results})



#courses related

#@login_required
#def course_list_view(request):
#    courses = Course.objects.all()
#    return render(request, 'quizzes/course_list.html', {'courses': courses})

def course_list_view(request):
    courses = Course.objects.all()
    applied_courses = AppliedCourse.objects.filter(user=request.user).values_list('course_id', flat=True)
    return render(request, 'quizzes/course_list.html', {
        'courses': courses,
        'applied_courses': applied_courses,
    })


@login_required
def apply_to_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    if AppliedCourse.objects.filter(user=user, course=course).exists():
        return HttpResponseForbidden("You have already applied to this course.")

    AppliedCourse.objects.create(user=user, course=course)

    return redirect('my_courses')  # Redirect to the user's courses page

@login_required
def my_courses_view(request):
    applied_courses = AppliedCourse.objects.filter(user=request.user)
    return render(request, 'quizzes/my_courses.html', {'applied_courses': applied_courses})

#@login_required
#def course_statistics_view(request, course_id):
#    course = get_object_or_404(Course, id=course_id)
#    applied_courses = AppliedCourse.objects.filter(course=course).select_related('user').order_by('applied_at')
#    applied_users_count = applied_courses.count()
#    lectures_count = Lecture.objects.filter(course=course).count()
#    last_applied_user_time = applied_courses.last().applied_at if applied_courses.exists() else None
#    
#    context = {
#        'course': course,
#        'applied_users_count': applied_users_count,
#        'lectures_count': lectures_count,
#        'applied_courses': applied_courses,
#        'last_applied_user_time': last_applied_user_time,
#    }
#    
#    return render(request, 'quizzes/course_statistics.html', context)

@login_required
def course_statistics_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    applied_users = AppliedCourse.objects.filter(course=course)
    
    # Calculate statistics
    applied_users_count = applied_users.count()
    last_applied_user_time = applied_users.order_by('-applied_at').first().applied_at if applied_users_count > 0 else None
    lectures_count = course.lectures.count()

    completed_lectures_data = []
    for applied_course in applied_users:
        # Count distinct completed lectures
        completed_lectures = LectureCompletion.objects.filter(user=applied_course.user, lecture__course=course).values('lecture').distinct()
        completed_lectures_count = completed_lectures.count()
        
        # Calculate the average of the highest score for each completed lecture
        best_scores = LectureCompletion.objects.filter(user=applied_course.user, lecture__course=course).values('lecture').annotate(best_score=Max('score'))
        average_best_score = best_scores.aggregate(Avg('best_score'))['best_score__avg']

        completed_lectures_data.append({
            'user': applied_course.user,
            'applied_at': applied_course.applied_at,
            'completed_lectures_count': completed_lectures_count,
            'average_best_score': average_best_score,
        })

    return render(request, 'quizzes/course_statistics.html', {
        'course': course,
        'applied_users_count': applied_users_count,
        'last_applied_user_time': last_applied_user_time,
        'lectures_count': lectures_count,
        'completed_lectures_data': completed_lectures_data,
    })

@login_required
def user_lecture_statistics_view(request, course_id, user_id):
    course = get_object_or_404(Course, id=course_id)
    user = get_object_or_404(User, id=user_id)
    lectures = Lecture.objects.filter(course=course)
    lecture_completions = LectureCompletion.objects.filter(user=user, lecture__course=course)

    # Organize the completion data by lecture
    lecture_stats = []
    for lecture in lectures:
        attempts = lecture_completions.filter(lecture=lecture)
        lecture_stats.append({
            'lecture': lecture,
            'attempts': attempts
        })

    return render(request, 'quizzes/user_lecture_statistics.html', {
        'course': course,
        'user': user,
        'lecture_stats': lecture_stats,
    })


@login_required
def create_course_view(request):
    #print("TESTTESTTESTTESTTESTTESTTESTTESTTESTTESTTEST")
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.creator = request.user
            course.save()
            print(f"Created course: {course.name}")

            # Create a blank lecture and a page for the new course
            lecture = Lecture.objects.create(course=course, title="Бұл алғашқы, сәлемдесу дәрісі", description="Бұл бірінші дәріс")
            print(f"Created lecture: {lecture.title}")

            LecturePage.objects.create(lecture=lecture, page_number=1, content="Қош келдіңіздер!", video_url="", image="", files="")
            print("Created first lecture page")

            return redirect('course_detail', course_id=course.id)
    else:
        form = CourseForm()
    return render(request, 'quizzes/create_course.html', {'form': form})

@login_required
def course_detail_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lectures = Lecture.objects.filter(course=course).order_by('lecture_number')
    return render(request, 'quizzes/course_detail.html', {
        'course': course,
        'lectures': lectures,
    })

@login_required
def delete_course_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user != course.creator:
        return HttpResponseForbidden("Вы не создатель курса")
    if request.method == 'POST':
        course.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def add_lecture_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.creator != request.user:
        return HttpResponseForbidden("Вы не создатель курса")

    if request.method == 'POST':
        form = LectureForm(request.POST)
        if form.is_valid():
            lecture = form.save(commit=False)
            lecture.course = course
            lecture.save()
            return redirect('edit_lecture', course_id=course.id, lecture_id=lecture.id)
    else:
        form = LectureForm()
    return render(request, 'quizzes/add_lecture.html', {'form': form, 'course': course})

@login_required
def add_lecture_page_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id)

    if request.method == 'POST':
        form = LecturePageForm(request.POST, request.FILES)
        if form.is_valid():
            lecture_page = form.save(commit=False)
            lecture_page.lecture = lecture
            
            # Assign the next available page number starting from 1 from this lecture
            existing_page_numbers = lecture.pages.values_list('page_number', flat=True)
            next_page_number = 1
            while next_page_number in existing_page_numbers:
                next_page_number += 1
            lecture_page.page_number = next_page_number

            lecture_page.save()
            return redirect('edit_lecture', course_id=course_id, lecture_id=lecture_id)
    else:
        form = LecturePageForm()

    return render(request, 'quizzes/add_lecture_page.html', {
        'course': course,
        'lecture': lecture,
        'form': form,
    })




@login_required
def delete_lecture_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course_id=course_id)
    
    if course.creator != request.user:
        return HttpResponseForbidden("Вы не создатель курса")
    
    if request.method == 'POST':
        lecture.delete()
        return redirect('course_detail', course_id=course_id)
    return render(request, 'quizzes/delete_lecture.html', {'lecture': lecture})


@login_required
def take_lecture_page_view(request, course_id, lecture_id, page_number):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
    page = get_object_or_404(LecturePage, page_number=page_number, lecture=lecture)
    
    # Get the next and previous pages
    next_page = LecturePage.objects.filter(lecture=lecture, page_number=page.page_number + 1).first()
    previous_page = LecturePage.objects.filter(lecture=lecture, page_number=page.page_number - 1).first()

    if request.method == 'POST':
        # Handle the form submission
        return redirect('answer_status', course_id=course.id, lecture_id=lecture.id)

    return render(request, 'quizzes/take_lecture_page.html', {
        'course': course,
        'lecture': lecture,
        'page': page,
        'next_page': next_page,
        'previous_page': previous_page,
        'page_number': page_number,  # page_number должна передаваться
    })




@login_required
def add_question_view(request, course_id, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    if lecture.course.creator != request.user:
        return HttpResponseForbidden("You are not the creator of this course")

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.lecture = lecture
            question.save()
            return redirect('edit_lecture', course_id=course_id, lecture_id=lecture_id)
    else:
        form = QuestionForm()
    return render(request, 'quizzes/add_question.html', {'form': form, 'lecture': lecture})


@login_required
def answer_status_view(request, course_id, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id, course_id=course_id)
    if request.method == 'POST':
        user_answers = []
        for i, question in enumerate(lecture.questions.all()):
            user_answer = request.POST.get(f'question{i+1}')
            user_answers.append((question, user_answer))
        return render(request, 'quizzes/answer_status.html', {
            'lecture': lecture,
            'user_answers': user_answers,
        })
    return redirect('take_lecture', course_id=course_id, lecture_id=lecture_id)

@login_required
def create_lecture_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.creator != request.user:
        return HttpResponseForbidden("You are not the creator of this course")

    if request.method == 'POST':
        form = LectureForm(request.POST)
        if form.is_valid():
            lecture = form.save(commit=False)
            lecture.course = course
            lecture.save()
            return redirect('edit_lecture', course_id=course.id, lecture_id=lecture.id)
    else:
        form = LectureForm()
    return render(request, 'quizzes/add_lecture.html', {'form': form, 'course': course})



@login_required
def edit_lecture_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id)
    if course.creator != request.user:
        return HttpResponseForbidden("You are not the creator of this course")

    pages = lecture.pages.all()
    return render(request, 'quizzes/edit_lecture.html', {'lecture': lecture, 'pages': pages, 'course': course})



@login_required
def edit_lecture_page_view(request, course_id, lecture_id, page_number):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id)
    lecture_page = get_object_or_404(LecturePage, lecture=lecture, page_number=page_number)

    if request.method == 'POST':
        form = LecturePageForm(request.POST, request.FILES, instance=lecture_page)
        if form.is_valid():
            form.save()
            return redirect('edit_lecture', course_id=course_id, lecture_id=lecture_id)
    else:
        form = LecturePageForm(instance=lecture_page)

    return render(request, 'quizzes/edit_lecture_page.html', {
        'course': course,
        'lecture': lecture,
        'lecture_page': lecture_page,
        'form': form,
    })



@login_required
def create_lecture_page_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)

    # Check if this is the first page for the lecture
    if not lecture.pages.exists():
        # Create a default "Hello" page
        LecturePage.objects.create(
            lecture=lecture,
            page_number=1,
            content=f"Добро пожаловать на первую лекцию {course.name} курса"
        )

    if request.method == 'POST':
        form = LecturePageForm(request.POST, request.FILES)
        if form.is_valid():
            lecture_page = form.save(commit=False)
            lecture_page.lecture = lecture
            # Find the first available page number
            existing_page_numbers = list(lecture.pages.values_list('page_number', flat=True))
            page_number = 1
            while page_number in existing_page_numbers:
                page_number += 1
            lecture_page.page_number = page_number
            lecture_page.save()
            return redirect('edit_lecture', course_id=course.id, lecture_id=lecture.id)
    else:
        form = LecturePageForm()

    return render(request, 'quizzes/create_lecture_page.html', {
        'form': form,
        'course': course,
        'lecture': lecture,
    })

@login_required
def delete_lecture_page_view(request, course_id, lecture_id, page_number):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
    page = get_object_or_404(LecturePage, page_number=page_number, lecture=lecture)
    
    if request.method == 'GET':
        page.delete()
        
        # Adjust page numbers
        subsequent_pages = LecturePage.objects.filter(lecture=lecture, page_number__gt=page_number)
        for subsequent_page in subsequent_pages:
            subsequent_page.page_number -= 1
            subsequent_page.save()
        
        return redirect('edit_lecture', course_id=course.id, lecture_id=lecture.id)
    
    return redirect('edit_lecture', course_id=course.id, lecture_id=lecture.id)



@login_required
def create_test_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.lecture = lecture
            question.save()
            return redirect('edit_lecture', course_id=course.id, lecture_id=lecture.id)
    else:
        form = QuestionForm()
    
    return render(request, 'quizzes/create_test.html', {
        'form': form,
        'course': course,
        'lecture': lecture,
    })


#@login_required
#def manage_lecture_test_view(request, course_id, lecture_id):
#    course = get_object_or_404(Course, id=course_id)
#    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
#    
#    test_page, created = LectureTestPage.objects.get_or_create(lecture=lecture)
#
#    if request.method == 'POST':
#        # You can add logic here to handle saving the test or other post actions if needed
#        return redirect('course_detail', course_id=course.id)
#
#    questions = test_page.questions.all()
#    return render(request, 'quizzes/manage_lecture_test.html', {
#        'course': course,
#        'lecture': lecture,
#        'questions': questions
#    })

@login_required
def manage_lecture_test_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id)
    test_page, created = LectureTestPage.objects.get_or_create(lecture=lecture)
    questions = Question.objects.filter(test_page=test_page)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.test_page = test_page
            question.save()
            return redirect('manage_lecture_test', course_id=course.id, lecture_id=lecture.id)
    else:
        form = QuestionForm()

    context = {
        'course': course,
        'lecture': lecture,
        'questions': questions,
        'form': form,
    }
    return render(request, 'quizzes/manage_lecture_test.html', context)

@login_required
def add_question_view(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
    test_page = get_object_or_404(LectureTestPage, lecture=lecture)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.lecture_test_page = test_page
            question.save()
            return redirect('manage_lecture_test', course_id=course.id, lecture_id=lecture.id)
    else:
        form = QuestionForm()
    
    return render(request, 'quizzes/add_question.html', {
        'course': course,
        'lecture': lecture,
        'form': form
    })

#@login_required
#def edit_question_view(request, course_id, lecture_id, question_id):
#    course = get_object_or_404(Course, id=course_id)
#    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
#    question = get_object_or_404(Question, id=question_id, lecture_test_page__lecture=lecture)
#
#    if request.method == 'POST':
#        form = QuestionForm(request.POST, instance=question)
#        if form.is_valid():
#            form.save()
#            return redirect('manage_lecture_test', course_id=course.id, lecture_id=lecture.id)
#    else:
#        form = QuestionForm(instance=question)
#    
#    return render(request, 'quizzes/edit_question.html', {
#        'course': course,
#        'lecture': lecture,
#        'form': form
#    })

@login_required
def edit_question_view(request, course_id, lecture_id, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect('manage_lecture_test', course_id=course_id, lecture_id=lecture_id)
    else:
        form = QuestionForm(instance=question)

    context = {
        'course_id': course_id,
        'lecture_id': lecture_id,
        'form': form,
    }
    return render(request, 'quizzes/edit_question.html', context)

#@login_required
#def delete_question_view(request, course_id, lecture_id, question_id):
#    course = get_object_or_404(Course, id=course_id)
#    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
#    question = get_object_or_404(Question, id=question_id, lecture_test_page__lecture=lecture)
#
#    if request.method == 'POST':
#        question.delete()
#        return redirect('manage_lecture_test', course_id=course.id, lecture_id=lecture.id)
#
#    return render(request, 'quizzes/delete_question.html', {
#        'course': course,
#        'lecture': lecture,
#        'question': question
#    })

@login_required
def delete_question_view(request, course_id, lecture_id, question_id):
    question = get_object_or_404(Question, id=question_id)
    question.delete()
    return redirect('manage_lecture_test', course_id=course_id, lecture_id=lecture_id)



@login_required
def take_lecture_test_view(request, course_id, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    test_page = get_object_or_404(LectureTestPage, lecture=lecture)
    questions = Question.objects.filter(test_page=test_page)
    
    user_attempt = UserLectureAttempt.objects.get_or_create(user=request.user, lecture=lecture)[0]


    #TEMP ВРЕМЕННО TEMP ВРЕМЕННО TEMP ВРЕМЕННО TEMP ВРЕМЕННО TEMP ВРЕМЕННО TEMP ВРЕМЕННО TEMP ВРЕМЕННО 
    #if not user_attempt.can_attempt():
    #    messages.error(request, "Сізде бұл сынаққа ешқандай әрекет қалмады.")
    #    return redirect('course_detail', course_id=course_id)  # Redirect to course detail or any other appropriate page


    if request.method == 'POST':
        if 'final_submission' in request.POST:
            # Handle final submission
            for question in questions:
                try:
                    answer = Answer.objects.get(user=request.user, question=question)
                    # Logic here for final submission, such as calculating scores
                except Answer.DoesNotExist:
                    # Handle cases where an answer was not submitted
                    pass

            user_attempt.completed_attempts += 1
            user_attempt.completed = True
            user_attempt.save()

            # Calculate the score
            correct_answers_count = Answer.objects.filter(user=request.user, question__test_page=test_page, is_correct=True).count()
            total_questions = questions.count()
            score = (correct_answers_count / total_questions) * 100

            # Save the lecture completion record
            LectureCompletion.objects.create(user=request.user, lecture=lecture, score=score)

            return redirect('show_test_results', course_id=course_id, lecture_id=lecture_id)
        
        # Handle save action (not final submission)
        else:
            question_id = request.POST.get('question_id')
            user_answer = request.POST.get('user_answer')
            question = get_object_or_404(Question, id=question_id)

            # Save user's answer, update if already exists
            if user_answer:
                answer, created = Answer.objects.update_or_create(
                    user=request.user,
                    question=question,
                    defaults={
                        'selected_option': user_answer,
                        'is_correct': (user_answer == getattr(question, f'option{question.correct_option}'))
                    }
                )

    # Update questions with user's selected answers
    for question in questions:
        question.user_selected_option = None
        try:
            answer = Answer.objects.get(user=request.user, question=question)
            question.user_selected_option = answer.selected_option
        except Answer.DoesNotExist:
            pass

    return render(request, 'quizzes/take_lecture_test.html', {
        'course_id': course_id,
        'lecture_id': lecture_id,
        'lecture': lecture,
        'questions': questions,
        'user_attempt': user_attempt,
    })


@login_required
def show_test_results_view(request, course_id, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    questions = Question.objects.filter(test_page__lecture=lecture)
    user_answers = Answer.objects.filter(user=request.user, question__in=questions)

    return render(request, 'quizzes/test_results.html', {
        'lecture': lecture,
        'questions': questions,
        'user_answers': user_answers,
    })






@login_required
def show_test_results(request, course_id, lecture_id):
    course = get_object_or_404(Course, id=course_id)
    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
    test_page = get_object_or_404(LectureTestPage, lecture=lecture)
    questions = Question.objects.filter(test_page=test_page)
    answers = Answer.objects.filter(user=request.user, question__in=questions)

    correct_answers = answers.filter(is_correct=True).count()
    total_questions = questions.count()

    return render(request, 'quizzes/show_test_results.html', {
        'course': course,
        'lecture': lecture,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'answers': answers,
    })


@login_required
def creator_view_results(request, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    test_page = get_object_or_404(LectureTestPage, lecture=lecture)
    questions = Question.objects.filter(test_page=test_page)
    student_answers = Answer.objects.filter(question__in=questions).select_related('user').order_by('user', 'question')

    students = {}
    for answer in student_answers:
        if answer.user not in students:
            students[answer.user] = {
                'correct': 0,
                'total': 0,
                'answers': []
            }
        students[answer.user]['total'] += 1
        if answer.is_correct:
            students[answer.user]['correct'] += 1
        students[answer.user]['answers'].append(answer)

    return render(request, 'quizzes/creator_view_results.html', {
        'lecture': lecture,
        'students': students,
    })

@login_required
def view_file(request, course_id, lecture_id, page_number, pk):
    page = get_object_or_404(LecturePage, pk=pk)
    file_url = request.build_absolute_uri(page.files.url)

    return render(request, 'quizzes/view_file.html', {
        'file_url': file_url,
    })

@login_required
def edit_course_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.creator:
        return redirect('some_error_page')  # Optionally handle unauthorized access

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_detail', course_id=course.id)  # Redirect to the course detail page after saving
    else:
        form = CourseForm(instance=course)

    return render(request, 'quizzes/edit_course.html', {'form': form, 'course': course})

@login_required
def edit_survey_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user != course.creator:
        return redirect('course_detail', course_id=course.id)
    
    try:
        survey = course.surveys.get(course=course)
    except CourseSurvey.DoesNotExist:
        survey = None

    if request.method == 'POST':
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.course = course
            survey.save()
            return redirect('course_detail', course_id=course.id)
    else:
        form = SurveyForm(instance=survey)

    return render(request, 'quizzes/edit_survey.html', {'form': form, 'course': course})