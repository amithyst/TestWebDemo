
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
    
    # --- 赌场大厅 ---
    path("casino/", views.casino_lobby, name="casino_lobby"),

    # --- 具体游戏页面 (HTML) ---
    path("casino/game/rps/", views.game_view_rps, name="game_view_rps"), # 石头剪刀布页面
    path("casino/game/zjh/", views.game_view_zjh, name="game_view_zjh"), # 扎金花页面

    # --- 统一的游戏 API (处理下注) ---
    path("casino/api/play/<str:game_type>/", views.casino_api, name="casino_api"),

    # --- 🔥 进阶版交互式游戏 (需要 GameSession) ---
    # 1. 沉浸式扎金花 (可看牌、加注)
    path("casino/game/zjh_pro/", views.game_view_zjh_pro, name="game_view_zjh_pro"),
    # 2. 21点 (要牌/停牌)
    path("casino/game/blackjack/", views.game_view_blackjack, name="game_view_blackjack"),
    
    # --- 🔥 统一动作 API (处理 Start, Hit, Stand, Look, Bet 等动作) ---
    path("casino/api/action/", views.casino_action_api, name="casino_action_api"),
    

    # --- 其他页面 ---
    path("book/", views.book_index, name="book_index"),

    # --- API URL ---
    path('api/get-components/', views.get_compatible_components, name='api_get_components'),
]