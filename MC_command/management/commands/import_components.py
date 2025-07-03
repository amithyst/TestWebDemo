import os
import json
from django.core.management.base import BaseCommand, CommandError

from MC_command.models import (MinecraftVersion, Material, ItemType, 
                               Enchantment, AttributeType, PotionEffectType,
                               BooleanComponentType
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
        else:
            self.stdout.write(self.style.WARNING(f'No specific importer for "{file_path}". Please check the filename.'))
            # 更新提示信息，加入新的可用文件
            self.stdout.write(self.style.WARNING('Available files: versions.json, materials.json, item_types.json, enchantments.json, attributes.json, effects.json'))

        self.stdout.write(self.style.SUCCESS('Import process finished.'))