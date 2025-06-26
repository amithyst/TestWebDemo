# amithyst/testwebdemo/TestWebDemo-ceeff3e1a5759590a82ab87ba1c6ca503dc97842/MC_command/forms.py
'''
总结
通过上述对单一文件 forms.py 的修改，我们已经达成了您的所有目标：

统一的下拉列表格式：现在，无论是在创建/编辑命令的前台页面，还是在 Django Admin 中，附魔的下拉列表都会以 [种类] 名称 (版本范围) 的格式显示。
统一的排序：所有附魔下拉列表都会按照“种类”和“版本”进行排序，方便您查找。
代码高复用性 (DRY)：由于 admin.py 中的 AppliedEnchantmentInline 已配置为使用 AppliedEnchantmentForm，
我们无需在 Admin 中编写任何重复代码，实现了“一次修改，处处生效”的效果。
'''
import json
from django import forms
from .models import (
    GeneratedCommand, MinecraftVersion, Material, ItemType, 
    Enchantment,AppliedEnchantment, AttributeType, AppliedAttribute, 
    PotionEffectType,AppliedPotionEffect, AppliedFireworkExplosion
)
from .widgets import ColorPickerWidget # <--- 导入我们的小部件

# --- 新增：自定义模型选择字段 ---
class VersionedModelChoiceField(forms.ModelChoiceField):
    """
    一个自定义的模型选择字段，用于在下拉选项中显示版本的兼容范围。
    """
    def label_from_instance(self, obj):
        prefix = ""
        # --- 修改开始: 检查对象是否为附魔，如果是则添加类型前缀 ---
        # 使用 hasattr 确保此字段也能用于其他没有 get_enchant_type_display 方法的模型（如 AttributeType）
        if hasattr(obj, 'get_enchant_type_display'):
            prefix = f"[{obj.get_enchant_type_display()}] "
        # --- 修改结束 ---

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
        
        return f"{prefix}{obj.name}{version_range}"
    
class GeneratedCommandForm(forms.ModelForm):
    # 修改: 不再使用 base_item，而是直接使用 material 和 item_type
    material = forms.ModelChoiceField(
        queryset=Material.objects.all(),
        required=False, # 允许为空
        label="材质",
        help_text="选择物品的材质。可以只选材质，不选类型（如：钻石）。"
    )
    item_type = forms.ModelChoiceField(
        queryset=ItemType.objects.all(),
        required=False, # 允许为空
        label="物品类型",
        help_text="选择物品的基础类型。可以只选类型，不选材质（如：三叉戟）。"
    )

    class Meta:
        model = GeneratedCommand
        # 修改: 更新字段列表
        fields = ['title', 'target_version', 'material', 'item_type', 'custom_name', 'lore', 'count']
        labels = {
            'title': '配置名称',
            'target_version': '目标Minecraft版本',
            'custom_name': '自定义物品名称',
            'lore': '描述文本 (Lore)',
            'count': '数量',
        }

    def clean(self):
        # 新增: 验证逻辑，确保材质和类型至少选一个
        cleaned_data = super().clean()
        material = cleaned_data.get("material")
        item_type = cleaned_data.get("item_type")

        if not material and not item_type:
            # 添加一个非字段错误
            raise forms.ValidationError(
                "错误：您必须至少选择一种材质或一种物品类型。",
                code='incomplete_item'
            )
        return cleaned_data

class AppliedEnchantmentForm(forms.ModelForm):
    """附魔内联表单"""
    # --- MODIFICATION: Use the new custom field and add widget attributes ---
    enchantment = VersionedModelChoiceField(
        queryset=Enchantment.objects.select_related('min_version', 'max_version').all().order_by('enchant_type'),
        label="附魔",
        widget=forms.Select(attrs={
            'class': 'version-filtered-select',
            'data-component-type': 'enchantment'
        })
    )
    
    class Meta:
        model = AppliedEnchantment
        fields = ['enchantment', 'level']
        labels = {
            'level': '等级'
        }

class AppliedAttributeForm(forms.ModelForm):
    """属性内联表单"""
    # --- MODIFICATION: Use the new custom field and add widget attributes ---
    attribute = VersionedModelChoiceField(
        queryset=AttributeType.objects.select_related('min_version', 'max_version').all().order_by('name'),
        label="属性",
        widget=forms.Select(attrs={
            'class': 'version-filtered-select',
            'data-component-type': 'attribute'
        })
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

# ... (rest of the file is the same) ...

class AppliedPotionEffectForm(forms.ModelForm):
    """药水效果内联表单"""
    effect = VersionedModelChoiceField(
        queryset=PotionEffectType.objects.select_related('min_version', 'max_version').all().order_by('name'),
        label="药水效果",
        widget=forms.Select(attrs={
            'class': 'version-filtered-select',
            'data-component-type': 'potion_effect'
        })
    )
    
    class Meta:
        model = AppliedPotionEffect
        fields = ['effect', 'amplifier', 'duration', 'is_ambient', 'show_particles', 'show_icon']
        labels = {
            'amplifier': '等级',
            'duration': '持续时间 (ticks)',
            'is_ambient': '信标粒子',
            'show_particles': '显示粒子',
            'show_icon': '显示图标',
        }

# --- 在文件末尾添加以下新表单 ---
class AppliedFireworkExplosionForm(forms.ModelForm):
    class Meta:
        model = AppliedFireworkExplosion
        fields = ['shape', 'colors', 'fade_colors', 'has_trail', 'has_twinkle', 'repeat_count']
        widgets = {
            'colors': forms.HiddenInput(),
            'fade_colors': forms.HiddenInput(),
        }

    # --- 替换旧的 clean_colors 方法 ---
    def clean_colors(self):
        # 使用 .get() 并提供默认值，使其更安全
        data = self.cleaned_data.get('colors', '[]')
        # 如果JS发送了空字符串，则视为空列表
        if not data:
            data = '[]'
        
        if data == 'random':
            return data
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, list):
                raise forms.ValidationError("颜色必须是JSON列表格式。")
            return json.dumps(parsed)
        except json.JSONDecodeError:
            raise forms.ValidationError("无效的颜色JSON格式。")

    # --- 替换旧的 clean_fade_colors 方法 ---
    def clean_fade_colors(self):
        data = self.cleaned_data.get('fade_colors', '[]')
        if not data:
            data = '[]'
        
        if data == 'random':
            return data
        # 允许不填淡出颜色
        if data == '[]':
            return '[]'
            
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, list):
                raise forms.ValidationError("淡出颜色必须是JSON列表格式。")
            return json.dumps(parsed)
        except json.JSONDecodeError:
            raise forms.ValidationError("无效的淡出颜色JSON格式。")

class AppliedFireworkExplosionAdminForm(forms.ModelForm):
    class Meta:
        model = AppliedFireworkExplosion
        fields = '__all__'
        widgets = {
            'colors': ColorPickerWidget(),
            'fade_colors': ColorPickerWidget(),
        }
