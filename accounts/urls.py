from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.EmailTokenObtainPairView.as_view(), name='login'),  # changed
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.logout_view, name='logout'),

    # Current user
    path('me/', views.get_current_user, name='current-user'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('user/<str:username>/', views.UserDetailView.as_view(), name='user-detail'),

    # Search & Discovery
    path('search/', views.search_users, name='search-users'),
    path('discover/', views.discover_users, name='discover-users'),

    # Follow system
    path('follow/<str:username>/', views.follow_user, name='follow-user'),
    path('followers/<str:username>/', views.get_followers, name='get-followers'),
    path('following/<str:username>/', views.get_following, name='get-following'),
]