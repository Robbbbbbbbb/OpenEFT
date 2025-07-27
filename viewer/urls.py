from django.urls import path
from . import views

app_name = "viewer"
urlpatterns = [
    path('view', views.viewer, name='viewer'),
    path('save_edited_eft/', views.save_edited_eft, name='save_edited_eft'),
]
