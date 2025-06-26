from django.urls import path
from . import views

app_name = 'MC_command'

urlpatterns = [
    path("", views.home, name="home"),

    path("item/", views.item_index, name="item_index"),
    path("item/create/", views.create, name="create"),
    path("item/<int:command_id>/", views.detail, name="detail"),
    path("item/<int:command_id>/edit/", views.edit, name="edit"),
    path("item/<int:command_id>/delete/", views.delete, name="delete"),

    path("entity/", views.entity_index, name="entity_index"),
    path("book/", views.book_index, name="book_index"),

    # --- 新增：API URL ---
    path('api/get-components/', views.get_compatible_components, name='api_get_components'),
]
