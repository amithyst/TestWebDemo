# amithyst/testwebdemo/TestWebDemo-d3881865a0685c402e5482491f008b28a2027598/MC_command/admin.py
from .models import UserWallet, GameTransaction # <--- 记得在顶部导入新模型
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
    AppliedEntityComponent, EntityEquipmentSlot, TradeRecipe,
    AreaEffectCloudProperties # <-- 新增导入
)

# --- FIX: Import the custom forms ---
from .forms import (AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, 
                    AppliedFireworkExplosionAdminForm,AppliedBooleanComponentForm,
                    VersionedModelChoiceField, AppliedSpellForm
                    ,    # ... (existing forms) ...
                    GeneratedEntityForm, AppliedEntityComponentForm,
                    EntityEquipmentSlotForm, TradeRecipeForm,AreaEffectCloudPropertiesForm # <-- 新增导入
    ) # <--- 1. 在这里添加导入

# 3. --- Import the Generic Inlines from Django's contenttypes ---
from django.contrib.contenttypes.admin import GenericTabularInline
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


# ==============================================================================
# 新增: 实体相关模型的 ADMIN 定义
# ==============================================================================

# --- 注册实体基础数据模型 ---

@admin.register(EntityTag)
class EntityTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(EntityType)
class EntityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity_id')
    search_fields = ('name', 'entity_id')
    filter_horizontal = ('tags',) # 使用更友好的多对多选择器

@admin.register(EntityComponentType)
class EntityComponentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'nbt_key', 'value_type')
    search_fields = ('name', 'nbt_key')
    list_filter = ('value_type', 'tags')
    filter_horizontal = ('tags',)

# --- 为实体配置页面创建可复用的通用内联 ---

class GenericAppliedAttributeInline(GenericTabularInline):
    """
    一个【通用】的属性内联，可以附加到任何模型上 (此处用于实体)。
    """
    model = AppliedAttribute
    form = AppliedAttributeForm # 复用已有的表单
    extra = 1

class GenericAppliedPotionEffectInline(GenericTabularInline):
    """
    一个【通用】的药水效果内联 (此处用于实体)。
    """
    model = AppliedPotionEffect
    form = AppliedPotionEffectForm # 复用已有的表单
    extra = 1


# --- 为实体配置页面创建专用的内联 ---

class AppliedEntityComponentInline(admin.TabularInline):
    """内联：为实体添加自定义NBT组件。"""
    model = AppliedEntityComponent
    form = AppliedEntityComponentForm
    extra = 1
    autocomplete_fields = ('component_type',)

class EntityEquipmentSlotInline(admin.TabularInline):
    """内联：为实体添加装备。"""
    model = EntityEquipmentSlot
    form = EntityEquipmentSlotForm
    extra = 1
    verbose_name_plural = '实体装备'
    # 启用自动完成搜索框，方便从大量物品中选择
    autocomplete_fields = ('item',)

class TradeRecipeInline(admin.TabularInline):
    """内联：为村民/流浪商人添加交易。"""
    model = TradeRecipe
    form = TradeRecipeForm
    extra = 1
    verbose_name_plural = '村民交易配方'
    # 为所有物品选择字段启用自动完成
    autocomplete_fields = ('buy_item1', 'buy_item2', 'sell_item')


# mc_commands/admin.py

# ... (已有的 TradeRecipeInline 类)

# --- 新增：为粒子效果云创建内联 Admin ---
class AreaEffectCloudPropertiesInline(admin.StackedInline):
    """
    用于在实体页面内联编辑粒子效果云的属性。
    只会在实体类型是 area_effect_cloud 时显示（需要在JS中实现或由用户手动添加）。
    """
    model = AreaEffectCloudProperties
    form = AreaEffectCloudPropertiesForm
    extra = 0 # 默认不显示，需要用户点击添加
    can_delete = True
    verbose_name_plural = '粒子效果云（AEC）属性'
# --- 组装最终的实体 Admin 页面 ---


# mc_commands/admin.py

@admin.register(GeneratedEntity)
class GeneratedEntityAdmin(admin.ModelAdmin):
    """
    【修改后】实体配置的主 Admin 界面。
    """
    form = GeneratedEntityForm
    list_display = ('title', 'user', 'entity_type', 'updated_at')
    list_filter = ('user', 'entity_type')
    search_fields = ('title', 'entity_type__name')

    # --- 修改：添加新的内联和UI优化选项 ---
    inlines = [
        AreaEffectCloudPropertiesInline,  # <-- 新增：粒子效果云内联
        EntityEquipmentSlotInline,
        TradeRecipeInline,
        AppliedEntityComponentInline,
        GenericAppliedAttributeInline,
        GenericAppliedPotionEffectInline,
    ]

    # 使用左右选择框优化“乘客”字段的用户体验
    filter_horizontal = ('passengers',) 

    # 为“来源物品”外键字段启用搜索框，避免超长下拉列表
    autocomplete_fields = ('source_item',)

    # 将新字段添加到 fieldsets 中进行分组显示
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'entity_type')
        }),
        ('高级关联', {
            'classes': ('collapse',), # 默认折叠，保持界面整洁
            'fields': ('source_item', 'passengers')
        }),
    )

# --- 最后，为了让装备和交易的物品选择框能够搜索，我们需要在 GeneratedCommandAdmin 中配置搜索 ---
# (检查你已有的 GeneratedCommandAdmin，确保它有 search_fields)

# 检查 GeneratedCommandAdmin
# 你的 GeneratedCommandAdmin 已包含 search_fields，所以无需修改。
# 'search_fields = ('title', 'custom_name', 'material__display_name', 'item_type__display_name')'
# 这将允许 EntityEquipmentSlotInline 和 TradeRecipeInline 中的 autocomplete_fields 正常工作。


# ==============================================================================
# 赌博系统 Admin
# ==============================================================================

class GameTransactionInline(admin.TabularInline):
    model = GameTransaction
    extra = 0
    can_delete = False
    readonly_fields = ('created_at', 'trans_type', 'amount', 'description')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request, obj):
        return False # 在钱包页面不准直接加流水，防止逻辑混乱，去流水表加

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'vip_level_display', 'total_recharged', 'black_curtain_rate', 'is_flagged')
    list_filter = ('is_flagged', 'black_curtain_rate')
    search_fields = ('user__username',)
    
    # 余额和统计数据设为只读，强制管理员走流水，保证账目安全
    readonly_fields = ('balance', 'total_recharged', 'total_earnings', 'fee_rate_display')
    
    # 允许修改黑幕值
    fields = ('user', 'balance', 'total_recharged', 'total_earnings', 'fee_rate_display', 'black_curtain_rate', 'is_flagged')
    
    inlines = [GameTransactionInline]

    def vip_level_display(self, obj):
        return f"VIP {obj.vip_level}"
    vip_level_display.short_description = "VIP等级"

    def fee_rate_display(self, obj):
        return f"{obj.fee_rate * 100:.1f}%"
    fee_rate_display.short_description = "当前抽水比例"

@admin.register(GameTransaction)
class GameTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'trans_type', 'amount', 'created_at', 'description')
    list_filter = ('trans_type', 'created_at')
    search_fields = ('wallet__user__username', 'description')
    autocomplete_fields = ['wallet'] # 需要在UserWalletAdmin里配置search_fields
    
    def save_model(self, request, obj, form, change):
        """
        管理员在后台点'保存'时触发。
        注意：具体的余额更新逻辑在 models.py 的 save() 方法里，这里不需要重写，
        Django admin 默认会调用 model.save()。
        """
        super().save_model(request, obj, form, change)