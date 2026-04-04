from django.contrib import admin
from django.urls import path
from generator.views import index_page, text_view, write_tasks, take_answers

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index_page, name='index'),
    path('text_view/', text_view, name='text_view'),
    path('write_tasks/', write_tasks, name='write_tasks'),
    path('take_answers/', take_answers, name='take_answers'),
]
