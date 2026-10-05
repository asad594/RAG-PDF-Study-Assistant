from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_pdf),
    path("ask/", views.ask_question),
    path("quiz/", views.generate_quiz_view),
]