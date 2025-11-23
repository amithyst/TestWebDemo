import os
import json
from django.core.management.base import BaseCommand, CommandError

from MC_command.models import (MinecraftVersion, Material, ItemType, 
                               Enchantment, AttributeType, PotionEffectType,
                               BooleanComponentType, Spell  # <--- 1. 在这里导入 Spell 模型
                               ,# --- 新增：导入实体相关的模型 ---
                               EntityTag, EntityType, EntityComponentType,ParticleType
)

class Command(BaseCommand):
    help = 'Imports Minecraft components like versions, materials, item types, enchantments, attributes, and effects from a specified JSON file into the database.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The name of the JSON file in the json_data directory to import (e.g., versions.json).')

    def get_version_object(self, version_num, component_name, item_name):
        """
        一个辅助函数，用于获取版本对象并提供清晰的错误信息。
        """
        if not version_num:
            return None
        try:
            return MinecraftVersion.objects.get(version_number=version_num)
        except MinecraftVersion.DoesNotExist:
            raise CommandError(
                f'Error processing {component_name} "{item_name}":\n'
                f'MinecraftVersion "{version_num}" does not exist in the database.\n'
                f'Please add it to "versions.json" and run "python manage.py import_components versions.json" first.'
            )

    def import_versions(self, data):
        """导入Minecraft版本"""
        count = 0
        for version_data in data:
            version, created = MinecraftVersion.objects.update_or_create(
                version_number=version_data['version_number'],
                defaults={'ordering_id': version_data['ordering_id']}
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created version: {version.version_number}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new versions imported.'))

    # --- 新增：导入材质 ---
    def import_materials(self, data):
        """导入物品材质"""
        count = 0
        for mat_data in data:
            material, created = Material.objects.update_or_create(
                system_name=mat_data['system_name'],
                defaults={'display_name': mat_data.get('display_name', mat_data['system_name'])}
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created material: {material.display_name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new materials imported.'))

    # --- 新增：导入物品类型 ---
    def import_item_types(self, data):
        """导入物品类型"""
        count = 0
        for type_data in data:
            item_type, created = ItemType.objects.update_or_create(
                system_name=type_data['system_name'],
                defaults={
                    'display_name': type_data.get('display_name', type_data['system_name']),
                    'function_type': type_data.get('function_type', 'all')
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created item type: {item_type.display_name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new item types imported.'))
    
    def import_enchantments(self, data):
        """导入附魔"""
        count = 0
        for ench_data in data:
            min_version = self.get_version_object(ench_data.get('min_version'), 'enchantment', ench_data['name'])
            max_version = self.get_version_object(ench_data.get('max_version'), 'enchantment', ench_data['name'])

            enchantment, created = Enchantment.objects.update_or_create(
                enchant_id=ench_data['id'],
                defaults={
                    'name': ench_data['name'],
                    'max_level': ench_data.get('max_level', 1),
                    'min_version': min_version,
                    'max_version': max_version,
                    'enchant_type': ench_data.get('enchant_type', 'general')
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created enchantment: {enchantment.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new enchantments imported.'))

    def import_attributes(self, data):
        """导入属性"""
        count = 0
        for attr_data in data:
            min_version = self.get_version_object(attr_data.get('min_version'), 'attribute', attr_data['name'])
            max_version = self.get_version_object(attr_data.get('max_version'), 'attribute', attr_data['name'])
            
            attribute, created = AttributeType.objects.update_or_create(
                attribute_id=attr_data['id'],
                defaults={
                    'name': attr_data['name'],
                    'min_version': min_version,
                    'max_version': max_version,
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created attribute: {attribute.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new attributes imported.'))

    def import_potion_effects(self, data):
        """导入药水效果"""
        count = 0
        for effect_data in data:
            min_version = self.get_version_object(effect_data.get('min_version'), 'potion effect', effect_data['name'])
            max_version = self.get_version_object(effect_data.get('max_version'), 'potion effect', effect_data['name'])

            effect, created = PotionEffectType.objects.update_or_create(
                effect_id=effect_data['id'],
                defaults={
                    'name': effect_data['name'],
                    'min_version': min_version,
                    'max_version': max_version,
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created potion effect: {effect.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new potion effects imported.'))

    def import_boolean_components(self, data):
        count = 0
        for comp in data:
            min_v = self.get_version_object(comp.get('min_version'), 'boolean component', comp['name'])
            max_v = self.get_version_object(comp.get('max_version'), 'boolean component', comp['name'])

            obj, created = BooleanComponentType.objects.update_or_create(
                name=comp['name'],
                defaults={
                    'description': comp.get('description', ''),
                    'true_str': comp.get('true_str', ''),
                    'false_str': comp.get('false_str', ''),
                    'min_version': min_v,
                    'max_version': max_v,
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {obj.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} boolean components imported.'))

        # --- 2. 在此处添加新的 import_spells 函数 ---
    def import_spells(self, data):
        """导入法术"""
        count = 0
        for spell_data in data:
            # 获取版本对象，这会自动处理版本兼容性
            min_version = self.get_version_object(spell_data.get('min_version'), 'spell', spell_data['name'])
            max_version = self.get_version_object(spell_data.get('max_version'), 'spell', spell_data['name'])

            spell, created = Spell.objects.update_or_create(
                spell_id=spell_data['id'],
                defaults={
                    'name': spell_data['name'],
                    'min_version': min_version,
                    'max_version': max_version,
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created spell: {spell.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new spells imported.'))

    # --- 新增：导入实体标签 ---
    def import_entity_tags(self, data):
        """导入实体标签"""
        count = 0
        for tag_data in data:
            tag, created = EntityTag.objects.update_or_create(
                name=tag_data['name'],
                defaults={'description': tag_data.get('description', '')}
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created entity tag: {tag.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new entity tags imported.'))

    # --- 新增：导入实体类型 ---
    def import_entity_types(self, data):
        """导入实体类型及其标签关联"""
        count = 0
        for type_data in data:
            entity_type, created = EntityType.objects.update_or_create(
                entity_id=type_data['entity_id'],
                defaults={'name': type_data.get('name', type_data['entity_id'])}
            )

            # 处理多对多关系 (标签)
            if 'tags' in type_data:
                entity_type.tags.clear() # 清除旧的关联
                for tag_name in type_data['tags']:
                    try:
                        tag = EntityTag.objects.get(name=tag_name)
                        entity_type.tags.add(tag)
                    except EntityTag.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'  Tag "{tag_name}" not found for entity type "{entity_type.name}". Please import entity_tags.json first.'))
            
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created entity type: {entity_type.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new entity types imported.'))

    # --- 新增：导入实体组件类型 ---
    def import_entity_component_types(self, data):
        """导入实体组件类型及其标签关联"""
        count = 0
        for comp_data in data:
            component_type, created = EntityComponentType.objects.update_or_create(
                nbt_key=comp_data['nbt_key'],
                defaults={
                    'name': comp_data.get('name', comp_data['nbt_key']),
                    'value_type': comp_data.get('value_type', 'string'),
                    'description': comp_data.get('description', '')
                }
            )

            # 处理多对多关系 (标签)
            if 'tags' in comp_data:
                component_type.tags.clear()
                for tag_name in comp_data['tags']:
                    try:
                        tag = EntityTag.objects.get(name=tag_name)
                        component_type.tags.add(tag)
                    except EntityTag.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'  Tag "{tag_name}" not found for component type "{component_type.name}". Please import entity_tags.json first.'))

            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created entity component type: {component_type.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new entity component types imported.'))

    # --- 新增：导入粒子效果 ---
    def import_particles(self, data):
        """导入粒子效果类型"""
        count = 0
        for p_data in data:
            min_version = self.get_version_object(p_data.get('min_version'), 'particle', p_data['name'])
            max_version = self.get_version_object(p_data.get('max_version'), 'particle', p_data['name'])

            particle, created = ParticleType.objects.update_or_create(
                particle_id=p_data['id'],
                defaults={
                    'name': p_data['name'],
                    'min_version': min_version,
                    'max_version': max_version,
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created particle: {particle.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new particles imported.'))

    def handle(self, *args, **options):
        file_path = options['file_path']
        # 修正：移除旧的 '..' 片段，因为 'BASE_DIR' 已经指向项目根目录
        # 为了兼容性，我们保留原有逻辑，因为它能正确找到 'json_data' 目录
        json_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'json_data', file_path)

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'File not found at: {json_file_path}')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from file: {json_file_path}')

        if file_path == 'versions.json':
            self.stdout.write(self.style.HTTP_INFO('Importing Minecraft versions...'))
            self.import_versions(data)
        # --- 新增：处理 materials.json ---
        elif file_path == 'materials.json':
            self.stdout.write(self.style.HTTP_INFO('Importing materials...'))
            self.import_materials(data)
        # --- 新增：处理 item_types.json ---
        elif file_path == 'item_types.json':
            self.stdout.write(self.style.HTTP_INFO('Importing item types...'))
            self.import_item_types(data)
        elif file_path == 'enchantments.json':
            self.stdout.write(self.style.HTTP_INFO('Importing enchantments...'))
            self.import_enchantments(data)
        elif file_path == 'attributes.json':
            self.stdout.write(self.style.HTTP_INFO('Importing attributes...'))
            self.import_attributes(data)
        elif file_path == 'effects.json':
            self.stdout.write(self.style.HTTP_INFO('Importing potion effects...'))
            self.import_potion_effects(data)
        elif file_path == 'boolean_components.json':
            self.stdout.write(self.style.HTTP_INFO('Importing boolean components...'))
            self.import_boolean_components(data)
            # --- 3. 在此处添加对 spells.json 的处理 ---
        elif file_path == 'spells.json':
            self.stdout.write(self.style.HTTP_INFO('Importing spells...'))
            self.import_spells(data)
         # --- 新增：在这里添加对实体JSON文件的处理 ---
        elif file_path == 'entity_tags.json':
            self.stdout.write(self.style.HTTP_INFO('Importing entity tags...'))
            self.import_entity_tags(data)
        elif file_path == 'entity_types.json':
            self.stdout.write(self.style.HTTP_INFO('Importing entity types...'))
            self.import_entity_types(data)
        elif file_path == 'entity_component_types.json':
            self.stdout.write(self.style.HTTP_INFO('Importing entity component types...'))
            self.import_entity_component_types(data)
        # --- 新增 elif 块 ---
        elif file_path == 'particles.json':
            self.stdout.write(self.style.HTTP_INFO('Importing particles...'))
            self.import_particles(data)
        # --- 新增结束 ---

        else:
            self.stdout.write(self.style.WARNING(f'No specific importer for "{file_path}". Please check the filename.'))
            # --- 更新提示信息 ---
            self.stdout.write(self.style.WARNING(
                'Available files: versions.json, materials.json, item_types.json, enchantments.json, '
                'attributes.json, effects.json, boolean_components.json, spells.json, '
                'entity_tags.json, entity_types.json, entity_component_types.json, '
                'particles.json' # <-- 添加到提示
            ))
        self.stdout.write(self.style.SUCCESS('Import process finished.'))