# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/forms.py

from django import forms
from .models import (
    GeneratedCommand, MinecraftVersion, BaseItem, 
    AppliedEnchantment, AppliedAttribute, Enchantment, 
    AttributeType
)

# --- 新增：自定义模型选择字段 ---
class VersionedModelChoiceField(forms.ModelChoiceField):
    """
    一个自定义的模型选择字段，用于在下拉选项中显示版本的兼容范围。
    """
    def label_from_instance(self, obj):
        # 格式化版本范围字符串
        min_v = obj.min_version.version_number if obj.min_version else None
        max_v = obj.max_version.version_number if obj.max_version else None
        
        version_range = ""
        if min_v and max_v:
            if min_v == max_v:
                version_range = f" (仅 {min_v})"
            else:
                version_range = f" ({min_v} - {max_v})"
        elif min_v:
            version_range = f" ({min_v}+)"
        elif max_v:
            version_range = f" (最高 {max_v})"
        
        return f"{obj.name}{version_range}"
    
class GeneratedCommandForm(forms.ModelForm):
    class Meta:
        model = GeneratedCommand
        fields = ['title', 'target_version', 'base_item', 'custom_name', 'lore', 'count']
        labels = {
            'title': '配置名称',
            'target_version': '目标Minecraft版本',
            'base_item': '基础物品',
            'custom_name': '自定义物品名称',
            'lore': '描述文本 (Lore)',
            'count': '数量',
        }
class AppliedEnchantmentForm(forms.ModelForm):
    """附魔内联表单"""
    # --- 修改：使用新的自定义字段 ---
    enchantment = VersionedModelChoiceField(
        queryset=Enchantment.objects.select_related('min_version', 'max_version').all().order_by('name'),
        label="附魔"
    )
    
    class Meta:
        model = AppliedEnchantment
        fields = ['enchantment', 'level']
        labels = {
            'level': '等级'
        }

class AppliedAttributeForm(forms.ModelForm):
    """属性内联表单"""
    # --- 修改：使用新的自定义字段 ---
    attribute = VersionedModelChoiceField(
        queryset=AttributeType.objects.select_related('min_version', 'max_version').all().order_by('name'),
        label="属性"
    )

    class Meta:
        model = AppliedAttribute
        fields = ['attribute', 'modifier_name', 'amount', 'operation', 'slot']
        labels = {
            'modifier_name': '修饰符名称 (旧版)',
            'amount': '数量',
            'operation': '操作',
            'slot': '槽位'
        }