from django.urls import path
from . import views


urlpatterns = [
    path('course/create/', views.create_course_view, name='create_course'),
    path('course/<int:course_id>/', views.course_detail_view, name='course_detail'),
    path('course/<int:course_id>/edit/', views.edit_course_view, name='edit_course'),
    path('course/<int:course_id>/edit_survey/', views.edit_survey_view, name='edit_survey'),
    path('course/<int:course_id>/lecture/add/', views.create_lecture_view, name='add_lecture'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/edit/', views.edit_lecture_view, name='edit_lecture'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/delete/', views.delete_lecture_view, name='delete_lecture'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/take/<int:page_number>/', views.take_lecture_page_view, name='take_lecture_page'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/page/<int:page_number>/edit/', views.edit_lecture_page_view, name='edit_lecture_page'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/page/<int:page_number>/question/add/', views.add_question_view, name='add_question'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/page/<int:page_number>/delete/', views.delete_lecture_page_view, name='delete_lecture_page'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/page/create/', views.create_lecture_page_view, name='create_lecture_page'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/answer_status/', views.answer_status_view, name='answer_status'),

    path('course/<int:course_id>/lecture/<int:lecture_id>/test/manage/', views.manage_lecture_test_view, name='manage_lecture_test'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/test/question/add/', views.add_question_view, name='add_question'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/test/question/<int:question_id>/edit/', views.edit_question_view, name='edit_question'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/test/question/<int:question_id>/delete/', views.delete_question_view, name='delete_question'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/test/', views.take_lecture_test_view, name='take_lecture_test'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/test/results/', views.show_test_results, name='show_test_results'),

    path('course/<int:course_id>/delete/', views.delete_course_view, name='delete_course'),
    path('course/<int:course_id>/apply/', views.apply_to_course, name='apply_to_course'),
    path('lecture/<int:lecture_id>/results/', views.creator_view_results, name='creator_view_results'),
    path('course/<int:course_id>/statistics/', views.course_statistics_view, name='course_statistics'),
    path('course/<int:course_id>/statistics/user/<int:user_id>/', views.user_lecture_statistics_view, name='user_lecture_statistics'),
    path('courses/', views.course_list_view, name='course_list'),
    path('course/<int:course_id>/lecture/<int:lecture_id>/take/<int:page_number>/view-file/<int:pk>/', views.view_file, name='view_file'),

    path('my-courses/', views.my_courses_view, name='my_courses'),
] 