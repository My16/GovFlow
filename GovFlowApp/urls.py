from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

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
    path('documents/<int:pk>/forward/', views.forward_document, name='forward_document'),
    path('documents/receive/', views.receive_document, name='receive_document'),
    path("receive/", views.receive_page, name="receive_page"),
    path("receive/submit/", views.receive_document, name="receive_document"),
    path('documents/routing-slip/<int:pk>/', views.routing_slip_partial, name='routing_slip_partial'),
    path("notifications/read/<int:pk>/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/api/", views.notifications_api, name="notifications_api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)