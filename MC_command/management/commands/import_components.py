import os
import json
from django.core.management.base import BaseCommand, CommandError
from MC_command.models import MinecraftVersion, BaseItem, Enchantment, AttributeType, PotionEffectType

class Command(BaseCommand):
    help = 'Imports Minecraft components like versions, items, enchantments, attributes, and effects from a specified JSON file into the database.'

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

    def import_base_items(self, data):
        """导入基础物品"""
        count = 0
        for item_data in data:
            item, created = BaseItem.objects.update_or_create(
                item_id=item_data['item_id'],
                defaults={
                    'name': item_data['name'],
                    'item_type': item_data.get('item_type', 'other') 
                }
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f'  Successfully created item: {item.name}'))
        self.stdout.write(self.style.SUCCESS(f'Total {count} new items imported.'))
    
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
                    'enchant_type': ench_data.get('type', 'general')
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

    def handle(self, *args, **options):
        file_path = options['file_path']
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
        elif file_path == 'base_items.json':
            self.stdout.write(self.style.HTTP_INFO('Importing base items...'))
            self.import_base_items(data)
        elif file_path == 'enchantments.json':
            self.stdout.write(self.style.HTTP_INFO('Importing enchantments...'))
            self.import_enchantments(data)
        elif file_path == 'attributes.json':
            self.stdout.write(self.style.HTTP_INFO('Importing attributes...'))
            self.import_attributes(data)
        elif file_path == 'effects.json':
            self.stdout.write(self.style.HTTP_INFO('Importing potion effects...'))
            self.import_potion_effects(data)
        else:
            self.stdout.write(self.style.WARNING(f'No specific importer for "{file_path}". Please check the filename.'))
            self.stdout.write(self.style.WARNING('Available files: versions.json, base_items.json, enchantments.json, attributes.json, effects.json'))

        self.stdout.write(self.style.SUCCESS('Import process finished.'))