# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/urls.py
from django.urls import path
from . import views

# The app_name is crucial for namespacing URLs.
app_name = 'MC_command'

urlpatterns = [
    # ex: /MC_command/
    path("", views.index, name="index"),
    
    # ADDED: URL for creating a new command
    # ex: /MC_command/create/
    path("create/", views.create, name="create"),
    
    # ex: /MC_command/12/
    path("<int:command_id>/", views.detail, name="detail"),
    
    # ADDED: URL for editing an existing command
    # ex: /MC_command/12/edit/
    path("<int:command_id>/edit/", views.edit, name="edit"),
    
    # This URL already existed, and we will make its view functional.
    # ex: /MC_command/12/delete/
    path("<int:command_id>/delete/", views.delete, name="delete"),

    # --- 新增：API URL ---
    path('api/get-components/', views.get_compatible_components, name='api_get_components'),

]