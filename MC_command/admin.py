import re
from django.contrib import admin
from django.db.models import Q
from .models import (
    MinecraftVersion, BaseItem, Enchantment, PotionEffectType, AttributeType,
    GeneratedCommand, AppliedEnchantment, AppliedAttribute, AppliedPotionEffect, WrittenBookContent
)

# ... 之前的静态数据模型 Admin 定义保持不变 ...
@admin.register(MinecraftVersion)
class MinecraftVersionAdmin(admin.ModelAdmin):
    list_display = ('version_number', 'ordering_id')
    search_fields = ('version_number',)

@admin.register(BaseItem)
class BaseItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_id', 'min_version', 'max_version')
    search_fields = ('name', 'item_id')
    list_filter = ('min_version', 'max_version')

@admin.register(Enchantment)
class EnchantmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'enchant_id', 'min_version', 'max_version','max_level')
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
        # URL 格式通常是 /admin/app/model/object_id/change/
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
            # 检查字段是否是我们关心的那几个需要版本控制的字段
            if db_field.name in ["enchantment", "attribute", "effect"]:
                # 获取该字段的模型 (Enchantment, AttributeType, 等)
                model = db_field.related_model
                # 构建版本过滤查询
                version_q = (
                    Q(min_version__ordering_id__lte=target_version.ordering_id) | Q(min_version__isnull=True)
                ) & (
                    Q(max_version__ordering_id__gte=target_version.ordering_id) | Q(max_version__isnull=True)
                )
                # 应用过滤
                kwargs['queryset'] = model.objects.filter(version_q)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class WrittenBookContentInline(admin.StackedInline):
    model = WrittenBookContent
    can_delete = False
    verbose_name_plural = '书本内容'

class AppliedEnchantmentInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedEnchantment
    autocomplete_fields = ['enchantment']
    extra = 1

class AppliedAttributeInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedAttribute
    autocomplete_fields = ['attribute']
    extra = 1

class AppliedPotionEffectInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedPotionEffect
    autocomplete_fields = ['effect']
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
    inlines = [
        WrittenBookContentInline,
        AppliedEnchantmentInline,
        AppliedAttributeInline,
        AppliedPotionEffectInline
    ]