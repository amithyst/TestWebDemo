# amithyst/testwebdemo/TestWebDemo-d3881865a0685c402e5482491f008b28a2027598/MC_command/admin.py

import re
from django import forms
from django.contrib import admin
from django.db.models import Q
from .models import (
    MinecraftVersion, Material, ItemType, Enchantment, PotionEffectType, AttributeType,
    GeneratedCommand, AppliedEnchantment, AppliedAttribute, AppliedPotionEffect,
    AppliedFireworkExplosion, BooleanComponentType, AppliedBooleanComponent,
    WrittenBookContent, Spell, SpellInfusion, AppliedSpell # <--- 在这里添加新模型
       , # ... (existing models) ...
    EntityTag, EntityType, EntityComponentType, GeneratedEntity,
    AppliedEntityComponent, EntityEquipmentSlot, TradeRecipe
)

# --- FIX: Import the custom forms ---
from .forms import (AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, 
                    AppliedFireworkExplosionAdminForm,AppliedBooleanComponentForm,
                    VersionedModelChoiceField, AppliedSpellForm
                    ,    # ... (existing forms) ...
                    GeneratedEntityForm, AppliedEntityComponentForm,
                    EntityEquipmentSlotForm, TradeRecipeForm
    ) # <--- 1. 在这里添加导入


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
    list_display = ('display_name', 'system_name', 'function_type')
    search_fields = ('display_name', 'system_name', 'function_type')

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


@admin.register(Spell)
class SpellAdmin(admin.ModelAdmin):
    list_display = ('name', 'spell_id', 'min_version', 'max_version')
    search_fields = ('name', 'spell_id')
    list_filter = ('min_version', 'max_version')


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



class AppliedFireworkExplosionInline(admin.TabularInline):
    model = AppliedFireworkExplosion
    form = AppliedFireworkExplosionAdminForm # <--- 使用自定义表单
    extra = 1

class AppliedBooleanComponentInline(VersionedInlineMixin, admin.TabularInline):
    model = AppliedBooleanComponent
    form = AppliedBooleanComponentForm
    extra = 1


# --- 在此处添加法术注入相关的 Admin 和 Inline ---

class AppliedSpellInline(admin.TabularInline):
    """
    用于在 SpellInfusion 管理页面内联添加具体的法术。
    """
    model = AppliedSpell
    form = AppliedSpellForm  # <--- 2. 在这里指定使用新的表单
    extra = 1
    # 设置 autocomplete_fields 可以获得一个好用的搜索框
    autocomplete_fields = ['spell']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        重写此方法，为 'spell' 字段动态添加基于父对象版本的过滤。
        """
        if db_field.name == "spell":
            # 从请求的 URL 中解析出父对象 SpellInfusion 的 ID
            match = re.search(r'/spellinfusion/(\d+)/change', request.path_info)
            if match:
                object_id = match.group(1)
                try:
                    # 获取 SpellInfusion 对象，并进一步找到其关联的 GeneratedCommand
                    infusion_config = SpellInfusion.objects.get(pk=object_id)
                    target_version = infusion_config.command.target_version
                    
                    # 构建版本查询条件
                    version_q = (
                        Q(min_version__ordering_id__lte=target_version.ordering_id) | Q(min_version__isnull=True)
                    ) & (
                        Q(max_version__ordering_id__gte=target_version.ordering_id) | Q(max_version__isnull=True)
                    )
                    # 应用查询条件
                    kwargs['queryset'] = Spell.objects.filter(version_q)
                except SpellInfusion.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SpellInfusion)
class SpellInfusionAdmin(admin.ModelAdmin):
    """
    SpellInfusion 的独立管理页面。
    """
    list_display = ('__str__', 'command')
    # 将 AppliedSpellInline 嵌入到此页面
    inlines = [AppliedSpellInline]
    fields = ('command', 'spell_wheel', 'must_equip', 'max_spells')
    # command 字段设为只读，防止误操作
    readonly_fields = ('command',)


class SpellInfusionInline(admin.StackedInline):
    """
    用于在 GeneratedCommand 页面嵌入 SpellInfusion 的主要配置。
    """
    model = SpellInfusion
    # 设置为0，默认不显示，除非用户点击 "添加"
    extra = 0
    can_delete = False
    verbose_name_plural = '法术注入配置'
    # 移除 'command' 字段，因为它会被自动设置
    fields = ('spell_wheel', 'must_equip', 'max_spells')


# -----------------------------------------------------------------------------
# GeneratedCommand 的 Admin 定义 
# -----------------------------------------------------------------------------
@admin.register(GeneratedCommand)
class GeneratedCommandAdmin(admin.ModelAdmin):
    # 修正：将 'base_item' 替换为 'item_name'
    list_display = ('title', 'user', 'item_name', 'target_version', 'updated_at')
    
    # 修正：移除对 'base_item__name' 的过滤，改为按材质和类型过滤
    list_filter = ('target_version', 'user', 'material', 'item_type')
    
    search_fields = ('title', 'custom_name', 'material__display_name', 'item_type__display_name')
    inlines = [
        SpellInfusionInline,
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