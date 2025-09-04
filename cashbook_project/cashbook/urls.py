from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('book/add/', views.add_book, name='add_book'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('book/<int:book_id>/add/<str:transaction_type>/', views.add_entry, name='add_entry'),
    path('book/<int:book_id>/edit/<int:pk>/', views.edit_entry, name='edit_entry'),
    path('book/<int:book_id>/delete/<int:pk>/', views.delete_entry, name='delete_entry'),
    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    path('book/<int:book_id>/report/', views.generate_report, name='generate_report'),
    path('book/<int:book_id>/download/', views.download_report, name='download_report'),
    path('book/<int:book_id>/create_user/', views.create_user_for_book, name='create_user_for_book'),
    path('users/my/', views.manage_my_users, name='manage_my_users'),
    path('user/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    ]
# Total we have a 18 URLs for our Routes