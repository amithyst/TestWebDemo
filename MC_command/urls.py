# 1. 确保导入了 include 函数
from django.urls import path, include 
from django.contrib import admin
from . import views

# 添加 app_name 来创建URL命名空间，这在后面会非常有用！
app_name = 'MC_command'

urlpatterns = [
    # ex: /mc_commands/
    path("", views.index, name="index"),

    
    # ex: /mc_commands/12/
    path("<int:command_id>/", views.detail, name="detail"),
    
    # ex: /mc_commands/12/generate/
    path("<int:command_id>/generate/", views.generate, name="generate"),
    
    # ex: /mc_commands/12/delete/
    path("<int:command_id>/delete/", views.delete, name="delete"),
]