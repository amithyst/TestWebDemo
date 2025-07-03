from django.urls import path
from .views import ComponentListView, ComponentDetailView

# 这个变量是必须的，Django会查找它
app_name = 'nbt_builder'

urlpatterns = [
    # 路由到组件列表API -> /api/v1/components/?version=...
    path('components/', ComponentListView.as_view(), name='component-list'),
    
    # 路由到组件详情API -> /api/v1/components/<component_key>/?version=...
    path('components/<str:component_key>/', ComponentDetailView.as_view(), name='component-detail'),
]