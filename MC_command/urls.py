
# MC_command/urls.py

from django.urls import path
from . import views

app_name = 'MC_command'

urlpatterns = [
    # --- 主页 ---
    path("", views.home, name="home"),

    # --- 物品（Item）相关URL ---
    path("item/", views.item_index, name="item_index"),
    path("item/create/", views.create, name="create"),
    path("item/<int:command_id>/", views.detail, name="detail"),
    path("item/<int:command_id>/edit/", views.edit, name="edit"),
    path("item/<int:command_id>/delete/", views.delete, name="delete"),

    # --- 实体（Entity）相关URL ---
    path("entity/", views.entity_index, name="entity_index"),
    # --- 新增：为实体的增删改查添加URL路径 ---
    path("entity/create/", views.entity_create, name="entity_create"),
    path("entity/<int:entity_id>/", views.entity_detail, name="entity_detail"),
    path("entity/<int:entity_id>/edit/", views.entity_edit, name="entity_edit"),
    path("entity/<int:entity_id>/delete/", views.entity_delete, name="entity_delete"),
    # --- 新增结束 ---

    # --- 其他页面 ---
    path("book/", views.book_index, name="book_index"),

    # --- API URL ---
    path('api/get-components/', views.get_compatible_components, name='api_get_components'),
]