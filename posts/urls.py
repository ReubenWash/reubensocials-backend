from django.urls import path
from . import views

urlpatterns = [
    # -------------------------
    # POSTS
    # -------------------------
    path('', views.PostListCreateView.as_view(), name='post-list-create'),
    path('<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('trending/', views.TrendingPostsView.as_view(), name='trending-posts'),
    path('explore/', views.explore_posts, name='explore-posts'),
    path('user/<str:username>/', views.UserPostsView.as_view(), name='user-posts'),

    # -------------------------
    # INTERACTIONS
    # -------------------------
    path('<int:pk>/like/', views.like_post, name='like-post'),
    path('<int:pk>/share/', views.share_post, name='share-post'),

    # -------------------------
    # COMMENTS
    # -------------------------
    path('<int:post_id>/comments/', views.CommentListCreateView.as_view(), name='comment-list-create'),

    # -------------------------
    # EXCLUSIVE MEDIA
    # -------------------------
    path('<int:post_id>/video/', views.get_exclusive_video, name='exclusive-video'),
    path('<int:post_id>/image/', views.get_exclusive_image, name='exclusive-image'),
]