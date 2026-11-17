from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('ongoing/', views.OngoingProjectListView.as_view(), name='project_ongoing'),
    path('completed/', views.CompletedProjectListView.as_view(), name='project_completed'),
    path('new/', views.ProjectCreateView.as_view(), name='project_create'),
    path('export/', views.export_projects_csv, name='export_csv'),
    path('import/', views.import_projects_csv, name='import_csv'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('<int:pk>/upload-media/', views.upload_project_media, name='upload_media'),
]
