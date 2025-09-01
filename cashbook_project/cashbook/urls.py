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
    # path('users/', views.manage_users, name='manage_users'),
    path('book/<int:book_id>/report/', views.generate_report, name='generate_report'),
    path('book/<int:book_id>/download/', views.download_report, name='download_report'),
    # path('book/<int:book_id>/invite/', views.invite_member, name='invite_member'),
    path('book/<int:book_id>/create_user/', views.create_user_for_book, name='create_user_for_book'),
    # path('manage_users/book/<int:book_id>/', views.manage_users, name='manage_users'),
    path('user/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user/edit/<int:user_id>/book/<int:book_id>/', views.edit_user, name='edit_user'),
    path('user/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('user/delete/<int:user_id>/book/<int:book_id>/', views.delete_user, name='delete_user'),
    path('book/<int:book_id>/create_user/', views.create_user_for_book, name='create_user_for_book'),
    path('book/<int:book_id>/edit_user/<int:user_id>/', views.edit_user_for_book, name='edit_user_for_book'),
    path('book/<int:book_id>/delete_user/<int:user_id>/', views.delete_user_for_book, name='delete_user_for_book'),
    path('book/<int:book_id>/manage_users/', views.manage_users_for_book, name='manage_users_for_book'),
    
    ]


    # path('manage_users/book/<int:book_id>/', views.manage_users, name='manage_users'),
    # path('user/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    # path('user/edit/<int:user_id>/book/<int:book_id>/', views.edit_user, name='edit_user'),
    # path('user/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    # path('user/delete/<int:user_id>/book/<int:book_id>/', views.delete_user, name='delete_user'),
    # path('book/<int:book_id>/generate_report/', views.generate_report, name='generate_report'),
    # path('book/<int:book_id>/download_report/', views.download_report, name='download_report'),