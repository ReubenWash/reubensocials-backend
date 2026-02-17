from django.contrib import admin
from .models import Post, Like, Comment, PostPurchase

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'post_type', 'is_exclusive', 'likes_count', 'comments_count', 'created_at']
    list_filter = ['post_type', 'is_exclusive', 'created_at']
    search_fields = ['author__username', 'content']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    search_fields = ['user__username', 'content']

admin.site.register(Like)
admin.site.register(PostPurchase)