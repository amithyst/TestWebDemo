# amithyst/testwebdemo/TestWebDemo-d3881865a0685c402e5482491f008b28a2027598/MC_command/admin.py

import re
from django.contrib import admin
from django.db.models import Q
from .models import (
    MinecraftVersion, BaseItem, Enchantment, PotionEffectType, AttributeType,
    GeneratedCommand, AppliedEnchantment, AppliedAttribute, AppliedPotionEffect, WrittenBookContent
)
# --- FIX: Import the custom forms ---
from .forms import AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, VersionedModelChoiceField


# ... 之前的静态数据模型 Admin 定义保持不变 ...
@admin.register(MinecraftVersion)
class MinecraftVersionAdmin(admin.ModelAdmin):
    list_display = ('version_number', 'ordering_id')
    search_fields = ('version_number',)

@admin.register(BaseItem)
class BaseItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_id', 'item_type', 'min_version'
                    # , 'max_version'
                    )
    search_fields = ('name', 'item_id')
    list_filter = ('min_version', 'item_type')

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
            if db_field.name in ["enchantment", "attribute", "effect"]:
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

# -----------------------------------------------------------------------------
# GeneratedCommand 的 Admin 定义 (无需改变)
# -----------------------------------------------------------------------------
@admin.register(GeneratedCommand)
class GeneratedCommandAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'base_item', 'target_version', 'updated_at')
    list_filter = ('target_version', 'user', 'base_item__name')
    search_fields = ('title', 'user__username')
    fieldsets = [
        ('核心信息', {'fields': ['user', 'title', 'target_version', 'base_item']}),
        ('基础属性', {'fields': ['custom_name', 'lore', 'count'], 'classes': ['collapse']}),
    ]
    # The 'inlines' attribute will be dynamically set by get_inlines
    
    def get_inlines(self, request, obj=None):
        """
        Dynamically show the potion effects inline form ONLY if the base item type is 'potion'.
        """
        inlines = [WrittenBookContentInline, AppliedEnchantmentInline, AppliedAttributeInline]
        if obj and obj.base_item.item_type == 'potion':
            inlines.append(AppliedPotionEffectInline)
        return inlines