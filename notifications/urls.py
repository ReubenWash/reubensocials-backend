from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('read-all/', views.mark_all_notifications_read, name='mark-all-read'),
    path('unread-count/', views.unread_notification_count, name='unread-count'),
]