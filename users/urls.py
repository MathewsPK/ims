from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Auth
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Password reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Password change
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Admin user management
    path('manage/', views.UserListView.as_view(), name='user_list'),
    path('manage/new/', views.UserCreateView.as_view(), name='user_create'),
    path('manage/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('manage/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('manage/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
]
