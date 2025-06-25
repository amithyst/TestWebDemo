# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/views.py
from django import forms
# --- 在文件顶部，确保导入以下所有内容 ---
import json
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.forms import inlineformset_factory
from django.db import transaction

from django.http import JsonResponse
from django.db.models import Q
from .models import Enchantment, AttributeType

from .models import GeneratedCommand, AppliedEnchantment, AppliedAttribute, AppliedPotionEffect, MinecraftVersion, BaseItem # Add AppliedPotionEffect, BaseItem
from .forms import GeneratedCommandForm, AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, VersionedModelChoiceField # Add AppliedPotionEffectForm

# --- 核心视图 ---

@login_required
def index(request):
    command_list = GeneratedCommand.objects.filter(user=request.user).order_by("-updated_at")
    context = {
        'command_list': command_list,
    }
    return render(request, 'MC_command/index.html', context)

@login_required
def detail(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    command_context = _generate_command_context(command_obj)
    context = {
        'command': command_obj,
        'give_command_string': command_context['give_command'],
        'data_structure_json': command_context['data_json'],
    }
    return render(request, 'MC_command/detail.html', context)

# --- 增删改查 (CRUD) 视图 ---
# --- 完全替换旧的 CREATE 和 EDIT 视图 ---

@login_required
def create(request):
    """处理创建新命令及其关联的附魔和属性。"""
    EnchantmentFormSet = inlineformset_factory(GeneratedCommand, AppliedEnchantment, form=AppliedEnchantmentForm, extra=1, can_delete=True, min_num=0)
    AttributeFormSet = inlineformset_factory(GeneratedCommand, AppliedAttribute, form=AppliedAttributeForm, extra=1, can_delete=True, min_num=0)
    PotionEffectFormSet = inlineformset_factory(GeneratedCommand, AppliedPotionEffect, form=AppliedPotionEffectForm, extra=1, can_delete=True, min_num=0)

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST)
        enchant_formset = EnchantmentFormSet(request.POST, prefix='enchantments')
        attribute_formset = AttributeFormSet(request.POST, prefix='attributes')
        potion_formset = PotionEffectFormSet(request.POST, prefix='potions') # Add this

        if form.is_valid() and enchant_formset.is_valid() and attribute_formset.is_valid() and potion_formset.is_valid():
            try:
                with transaction.atomic(): # 保证数据库操作的原子性
                    # 版本兼容性验证 (优化 1)
                    target_version = form.cleaned_data['target_version']
                    _validate_version_compatibility(form, enchant_formset, attribute_formset, target_version)

                    command_instance = form.save(commit=False)
                    command_instance.user = request.user
                    command_instance.save()

                    enchant_formset.instance = command_instance
                    enchant_formset.save()

                    attribute_formset.instance = command_instance
                    attribute_formset.save()

                    potion_formset.instance = command_instance
                    potion_formset.save()
                    
                    return redirect(reverse('MC_command:detail', args=[command_instance.id]))
            except forms.ValidationError:
                # 如果验证失败，会抛出此异常，让表单显示错误
                pass

    else: # GET
        form = GeneratedCommandForm()
        enchant_formset = EnchantmentFormSet(prefix='enchantments')
        attribute_formset = AttributeFormSet(prefix='attributes')
        potion_formset = PotionEffectFormSet(prefix='potions') # Add this

    # ADD: Provide version data to the template
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    base_item_data = {i.pk: {'type': i.item_type} for i in BaseItem.objects.all()} # Add this

    context = {
        'form': form,
        'enchant_formset': enchant_formset,
        'attribute_formset': attribute_formset,
        'potion_formset': potion_formset, # Add this
        'form_title': '创建新命令',
        'version_data_json': json.dumps(version_data),
        'base_item_data_json': json.dumps(base_item_data) # Add this
    }
    return render(request, 'MC_command/command_form.html', context)



@login_required
def edit(request, command_id):
    """处理编辑命令及其关联的附魔和属性。"""
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    EnchantmentFormSet = inlineformset_factory(GeneratedCommand, AppliedEnchantment, form=AppliedEnchantmentForm, extra=1, can_delete=True, min_num=0)
    AttributeFormSet = inlineformset_factory(GeneratedCommand, AppliedAttribute, form=AppliedAttributeForm, extra=1, can_delete=True, min_num=0)
    PotionEffectFormSet = inlineformset_factory(GeneratedCommand, AppliedPotionEffect, form=AppliedPotionEffectForm, extra=1, can_delete=True, min_num=0) # Add this

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST, instance=command_obj)
        enchant_formset = EnchantmentFormSet(request.POST, instance=command_obj, prefix='enchantments')
        attribute_formset = AttributeFormSet(request.POST, instance=command_obj, prefix='attributes')
        potion_formset = PotionEffectFormSet(request.POST, instance=command_obj, prefix='potions') # Add this

        if form.is_valid() and enchant_formset.is_valid() and attribute_formset.is_valid() and potion_formset.is_valid():
            try:
                with transaction.atomic():
                    target_version = form.cleaned_data['target_version']
                    _validate_version_compatibility(form, enchant_formset, attribute_formset, target_version)
                    
                    form.save()
                    enchant_formset.save()
                    attribute_formset.save()
                    potion_formset.save()

                    return redirect(reverse('MC_command:detail', args=[command_obj.id]))
            except forms.ValidationError:
                pass
    else: # GET
        form = GeneratedCommandForm(instance=command_obj)
        enchant_formset = EnchantmentFormSet(instance=command_obj, prefix='enchantments')
        attribute_formset = AttributeFormSet(instance=command_obj, prefix='attributes')
        potion_formset = PotionEffectFormSet(instance=command_obj, prefix='potions')
    
    # ADD: Provide version data to the template
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    base_item_data = {i.pk: {'type': i.item_type} for i in BaseItem.objects.all()}
    
    context = {
        'form': form,
        'enchant_formset': enchant_formset,
        'attribute_formset': attribute_formset,
        'potion_formset': potion_formset,
        'command': command_obj,
        'form_title': '编辑命令',
        'version_data_json': json.dumps(version_data),
        # --- 确保下面这行代码存在且没有被注释 ---
        'base_item_data_json': json.dumps(base_item_data),
    }
    return render(request, 'MC_command/command_form.html', context)


# C:\Github\djangotutorial\MC_command\views.py

# ... (文件其他部分不变) ...

def _validate_version_compatibility(form, enchant_formset, attribute_formset, target_version):
    """
    一个辅助函数，用于检查所选版本是否与所有组件兼容。
    如果不兼容，则会向主表单添加一个错误并引发 ValidationError。
    """
    all_components = [form.cleaned_data.get('base_item')]
    for enchant_form in enchant_formset.cleaned_data:
        if enchant_form and not enchant_form.get('DELETE'):
            all_components.append(enchant_form.get('enchantment'))
    for attr_form in attribute_formset.cleaned_data:
        if attr_form and not attr_form.get('DELETE'):
            all_components.append(attr_form.get('attribute'))

    min_v_id = 0
    max_v_id = float('inf')

    # 计算所有组件版本号的交集
    for component in filter(None, all_components):
        # 修复: 在访问 .ordering_id 前检查对象是否存在
        if component.min_version:
            min_v_id = max(min_v_id, component.min_version.ordering_id)
        
        # 修复: 同样检查 max_version
        if component.max_version:
            max_v_id = min(max_v_id, component.max_version.ordering_id)

    # 新增: 检查是否存在有效的版本范围交集
    if min_v_id > max_v_id:
        min_v_str = MinecraftVersion.objects.get(ordering_id=min_v_id).version_number
        max_v_str = "更早版本"
        if max_v_id != float('inf'):
            max_v_str = MinecraftVersion.objects.get(ordering_id=max_v_id).version_number
        
        error_msg = f"组件冲突：所选组件之间没有兼容的Minecraft版本 (计算出的最低版本需求为 {min_v_str}，最高为 {max_v_str})。请调整您的选择。"
        # 引发一个非字段错误，它将显示在表单顶部
        raise forms.ValidationError(error_msg)

    # 现有逻辑: 检查用户选择的版本是否在有效范围内
    if not (min_v_id <= target_version.ordering_id <= max_v_id):
        min_v_str = MinecraftVersion.objects.get(ordering_id=min_v_id).version_number
        max_v_str = "最新"
        if max_v_id != float('inf'):
            max_v_str = MinecraftVersion.objects.get(ordering_id=max_v_id).version_number
        
        error_msg = f"版本不兼容。根据所选组件，可用版本应在 {min_v_str} 和 {max_v_str} 之间。"
        form.add_error('target_version', error_msg)
        raise forms.ValidationError(error_msg)
    

@login_required
@require_POST
def delete(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    command_obj.delete()
    return redirect(reverse('MC_command:index'))

# --- 辅助函数 ---


# --- 辅助函数 (Helper Functions) ---

def _uuid_to_int_array(uuid_obj):
    """将 UUID 对象转换为 Minecraft NBT 所需的整数数组格式。"""
    int_val = uuid_obj.int
    # 将128位整数分割为4个32位整数
    part1 = (int_val >> 96) & 0xFFFFFFFF
    part2 = (int_val >> 64) & 0xFFFFFFFF
    part3 = (int_val >> 32) & 0xFFFFFFFF
    part4 = int_val & 0xFFFFFFFF
    # 转换为有符号32位整数
    def to_signed(n):
        return n if n < 2**31 else n - 2**32
    return f"[I;{to_signed(part1)},{to_signed(part2)},{to_signed(part3)},{to_signed(part4)}]"



def _generate_command_context(command: GeneratedCommand) -> dict:
    target_version_id = command.target_version.ordering_id
    base_item_id = command.base_item.item_id
    if target_version_id >= 12005: # Minecraft 1.20.5+
        data_structure = _build_component_structure(command)
        data_string = ",".join([f"{key}={value}" for key, value in data_structure.items()])
        give_command = f"/give @p {base_item_id}[{data_string}] {command.count}"
    else: # Older versions
        data_structure = _build_nbt_tag_structure(command)
        data_string = json.dumps(data_structure, separators=(',', ':'))
        give_command = f"/give @p {base_item_id}{data_string} {command.count}"
    return {
        'give_command': give_command,
        'data_json': json.dumps(data_structure, indent=4, ensure_ascii=False),
    }

def _build_nbt_tag_structure(command: GeneratedCommand) -> dict:
    """构建旧版 (<=1.20.4) 的 NBT 标签结构"""
    nbt_data = {}
    display = {}

    if command.custom_name:
        display['Name'] = json.dumps(command.custom_name, ensure_ascii=False)

    if command.lore:
        lore_lines = [json.dumps(line, ensure_ascii=False) for line in command.lore.splitlines() if line.strip()]
        if lore_lines:
            display['Lore'] = f'[{",".join(lore_lines)}]'

    if display:
        nbt_data['display'] = display

    if command.enchantments.exists():
        nbt_data['Enchantments'] = [{'id': ench.enchantment.enchant_id, 'lvl': ench.level} for ench in command.enchantments.all()]
    
    # --- 新增：处理属性修饰符 ---
    if command.attributes.exists():
        modifier_list = []
        for attr in command.attributes.all():
            modifier = {
                "AttributeName": attr.attribute.attribute_id,
                "Name": attr.modifier_name,
                "Amount": attr.amount,
                "Operation": attr.operation,
                "Slot": attr.slot,
                "UUID": _uuid_to_int_array(attr.uuid) # 使用新的辅助函数
            }
            modifier_list.append(modifier)
        # NBT 的 AttributeModifiers 是一个字典列表，JSON 转换时会自动处理
        nbt_data['AttributeModifiers'] = modifier_list

    # --- ADDED: Handle Potion Effects for old versions ---
    if command.potion_effects.exists():
        effects_list = []
        for effect in command.potion_effects.all():
            effects_list.append({
                'Id': effect.effect.effect_id,
                'Amplifier': effect.amplifier,
                'Duration': effect.duration,
                'Ambient': 1 if effect.is_ambient else 0,
                'ShowParticles': 1 if effect.show_particles else 0,
                'ShowIcon': 1 if effect.show_icon else 0
            })
        nbt_data['CustomPotionEffects'] = effects_list

    return nbt_data

def _build_component_structure(command: GeneratedCommand) -> dict:
    """构建新版 (>=1.20.5) 的 Component 结构"""
    components = {}
    op_map = {0: "add_value", 1: "add_multiplied_base", 2: "add_multiplied_total"}

    if command.custom_name:
        components['minecraft:custom_name'] = json.dumps(command.custom_name, ensure_ascii=False)

    if command.lore:
        lore_lines = [json.dumps(line, ensure_ascii=False) for line in command.lore.splitlines() if line.strip()]
        if lore_lines:
            components['minecraft:lore'] = f'[{",".join(lore_lines)}]'

    if command.enchantments.exists():
        enchantment_dict = {f"{ench.enchantment.enchant_id}": ench.level for ench in command.enchantments.all()}
        components['minecraft:enchantments'] = f'{{levels:{json.dumps(enchantment_dict)}}}'

    # --- 新增：处理属性修饰符 ---
    if command.attributes.exists():
        modifier_list = []
        for attr in command.attributes.all():
            modifier = {
                "attribute": attr.attribute.attribute_id,
                # "name": attr.modifier_name,
                "amount": attr.amount,
                "operation": op_map.get(attr.operation, "add_value"), # 将数字映射为字符串
                "slot": attr.slot
            }
            modifier_list.append(modifier)
        # component 格式需要手动构造成字符串
        components['minecraft:attribute_modifiers'] = f'{{modifiers:{json.dumps(modifier_list, ensure_ascii=False)}}}'
    
    # --- ADDED: Handle Potion Effects for new versions ---
    if command.potion_effects.exists():
        effects_list = []
        for effect in command.potion_effects.all():
            effects_list.append({
                "id": effect.effect.effect_id,
                "amplifier": effect.amplifier,
                "duration": effect.duration,
                "ambient": effect.is_ambient,
                "show_particles": effect.show_particles,
                "show_icon": effect.show_icon
            })

        # Note the nested structure required by the component
        potion_contents = {'custom_effects': effects_list}
        components['minecraft:potion_contents'] = json.dumps(potion_contents, ensure_ascii=False, separators=(',', ':'))


    return components

# --- 新增：用于 AJAX 的 API 视图 ---
def get_compatible_components(request):
    version_pk = request.GET.get('version_id') # Changed variable name for clarity
    component_type = request.GET.get('type')

    if not version_pk or not component_type:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        # --- FIX: First, get the version object using its Primary Key (pk) ---
        target_version = get_object_or_404(MinecraftVersion, pk=int(version_pk))
        # --- FIX: Then, use its ordering_id for the query ---
        target_ordering_id = target_version.ordering_id
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid version_id'}, status=400)

    # 构建动态的版本过滤查询
    version_filter = (
        Q(min_version__ordering_id__lte=target_ordering_id) | Q(min_version__isnull=True)
    ) & (
        Q(max_version__ordering_id__gte=target_ordering_id) | Q(max_version__isnull=True)
    )

    if component_type == 'enchantment':
        queryset = Enchantment.objects.filter(version_filter)
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id': obj.pk, 'text': field.label_from_instance(obj)}
            for obj in queryset
        ]
    elif component_type == 'attribute':
        queryset = AttributeType.objects.filter(version_filter)
        field = VersionedModelChoiceField(queryset=queryset)
        # UPDATE: Include attribute_id in the response for attributes
        data = [
            {'id': obj.pk, 'text': field.label_from_instance(obj), 'attribute_id': obj.attribute_id}
            for obj in queryset
        ]
    else:
        return JsonResponse({'error': 'Invalid component type'}, status=400)
    
    return JsonResponse(data, safe=False)
    
