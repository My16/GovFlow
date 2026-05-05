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
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("documents/<int:pk>/return/", views.return_document, name="return_document"),
    path("documents/<int:pk>/complete/", views.complete_document, name="complete_document"),
    path("documents/completed/", views.completed_documents, name="completed_documents"),
    path("documents/<int:pk>/edit/modal/", views.edit_document_modal, name="edit_document_modal"),
    path("documents/<int:pk>/edit/", views.edit_document, name="edit_document"),
    path('documents/<int:pk>/retract/', views.retract_document, name='retract_document'),
    path("document/<int:document_id>/add_status/", views.add_status, name="add_status"),
    # path("reports/api/<str:report_type>/", views.document_report_api, name="document_report_api"),
    path("reports/api/<str:report_type>/", views.document_report_api, name="document_report_api"),
    path('users/',                 views.user_management,        name='user_management'),
    path('users/add/',             views.user_management_add,    name='user_management_add'),
    path('users/<int:pk>/edit/',   views.user_management_edit,   name='user_management_edit'),
    path('users/<int:pk>/delete/', views.user_management_delete, name='user_management_delete'),
    path('users/<int:pk>/toggle/', views.user_management_toggle, name='user_management_toggle'),
    path('settings/', views.settings, name='settings'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)