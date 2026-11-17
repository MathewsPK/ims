from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.ExpenseListView.as_view(), name='expense_list'),
    path('new/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_update'),
    path('<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    path('<int:pk>/review/', views.review_expense, name='expense_review'),
]
