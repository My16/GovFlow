from django.urls import path
from . import views

urlpatterns = [
    path('', views.loginpage, name='loginpage'),
    path('home/', views.homepage, name='homepage'),
    path('create-user/', views.create_user, name='create_user'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('documents/', views.all_documents, name='all_documents'),
    path('documents/new/', views.new_document, name='new_document'),
    path('documents/<int:pk>/', views.document_detail, name='document_detail'),
    path("delete/<int:pk>/", views.delete_document, name="delete_document"),
    path('documents/<int:pk>/pdf/', views.document_pdf, name='document_pdf'),
]