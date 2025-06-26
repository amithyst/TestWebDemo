# amithyst/testwebdemo/TestWebDemo-d3881865a0685c402e5482491f008b28a2027598/MC_command/admin.py

import re
from django import forms
from django.contrib import admin
from django.db.models import Q
from .models import (
    MinecraftVersion, Material, ItemType, Enchantment, PotionEffectType, AttributeType,
    GeneratedCommand, AppliedEnchantment, AppliedAttribute, AppliedPotionEffect,
    AppliedFireworkExplosion, BooleanComponentType, AppliedBooleanComponent,
    WrittenBookContent
)

# --- FIX: Import the custom forms ---
from .forms import (AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, 
                    AppliedFireworkExplosionAdminForm,AppliedBooleanComponentForm,
                    VersionedModelChoiceField)

from .widgets import ColorPickerWidget # <--- 导入我们的小部件

# ... 之前的静态数据模型 Admin 定义保持不变 ...
@admin.register(MinecraftVersion)
class MinecraftVersionAdmin(admin.ModelAdmin):
    list_display = ('version_number', 'ordering_id')
    search_fields = ('version_number',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    # 修正: 使用模型中真实存在的字段 'display_name' 和 'system_name'
    list_display = ('display_name', 'system_name')
    search_fields = ('display_name', 'system_name')

@admin.register(ItemType)
class ItemTypeAdmin(admin.ModelAdmin):
    # 修正: 使用模型中真实存在的字段 'display_name' 和 'system_name'
    list_display = ('display_name', 'system_name')
    search_fields = ('display_name', 'system_name')

@admin.register(Enchantment)
class EnchantmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'enchant_id', 'min_version'
                    # , 'max_version'
                    ,'max_level', 'enchant_type')
    list_filter = ('min_version', 'enchant_type')
    search_fields = ('name', 'enchant_id')

@admin.register(PotionEffectType)
class PotionEffectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'effect_id', 'min_version', 'max_version')
    search_fields = ('name', 'effect_id')

@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'attribute_id', 'min_version', 'max_version')
    search_fields = ('name', 'attribute_id')

@admin.register(BooleanComponentType)
class BooleanComponentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'true_str', 'false_str', 'min_version', 'max_version')
    search_fields = ('name', 'true_str', 'false_str')

# -----------------------------------------------------------------------------
# 增强版的内联定义
# -----------------------------------------------------------------------------

class VersionedInlineMixin:
    """
    一个 Mixin，包含动态过滤 queryset 的通用逻辑。
    """
    def get_parent_object(self, request):
        """通过解析请求的URL来获取父对象 (GeneratedCommand)"""
        match = re.search(r'/(\d+)/change', request.path_info)
        if match:
            object_id = match.group(1)
            try:
                return GeneratedCommand.objects.get(pk=object_id)
            except GeneratedCommand.DoesNotExist:
                return None
        return None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        核心方法：当渲染外键字段（如下拉菜单或搜索框）时，Django会调用此方法。
        我们在这里介入，修改其 queryset。
        """
        parent_command = self.get_parent_object(request)
        if parent_command:
            target_version = parent_command.target_version
            if db_field.name in ["enchantment", "attribute", "effect",
                                #  "firework_explosion", #没版本限制
                                 "boolean_component"]:
                model = db_field.related_model
                version_q = (
                    Q(min_version__ordering_id__lte=target_version.ordering_id) | Q(min_version__isnull=True)
                ) & (
                    Q(max_version__ordering_id__gte=target_version.ordering_id) | Q(max_version__isnull=True)
                )
                kwargs['queryset'] = model.objects.filter(version_q)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class WrittenBookContentInline(admin.StackedInline):
    model = WrittenBookContent
    can_delete = False
    verbose_name_plural = '书本内容'

class AppliedEnchantmentInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedEnchantment
    # --- FIX: Use the custom form and remove autocomplete ---
    form = AppliedEnchantmentForm
    extra = 1

class AppliedAttributeInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedAttribute
    # --- FIX: Use the custom form and remove autocomplete ---
    form = AppliedAttributeForm
    extra = 1

class AppliedPotionEffectInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedPotionEffect
    form = AppliedPotionEffectForm # Use the new form
    extra = 1



class AppliedFireworkExplosionInline(admin.TabularInline):
    model = AppliedFireworkExplosion
    form = AppliedFireworkExplosionAdminForm # <--- 使用自定义表单
    extra = 1

class AppliedBooleanComponentInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedBooleanComponent
    form = AppliedBooleanComponentForm
    extra = 1

# -----------------------------------------------------------------------------
# GeneratedCommand 的 Admin 定义 (无需改变)
# -----------------------------------------------------------------------------
@admin.register(GeneratedCommand)
class GeneratedCommandAdmin(admin.ModelAdmin):
    # 修正：将 'base_item' 替换为 'item_name'
    list_display = ('title', 'user', 'item_name', 'target_version', 'updated_at')
    
    # 修正：移除对 'base_item__name' 的过滤，改为按材质和类型过滤
    list_filter = ('target_version', 'user', 'material', 'item_type')
    
    search_fields = ('title', 'custom_name', 'material__display_name', 'item_type__display_name')
    inlines = [
        AppliedEnchantmentInline,
        AppliedAttributeInline,
        AppliedPotionEffectInline,
        AppliedFireworkExplosionInline,
        AppliedBooleanComponentInline,
        WrittenBookContentInline,
    ]
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'target_version')
        }),
        ('物品选择', {
            'fields': ('material', 'item_type', 'count')
        }),
        ('自定义文本', {
            'fields': ('custom_name', 'lore')
        }),
    )