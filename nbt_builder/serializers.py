from rest_framework import serializers
from .models import (
    Component,
    StructureDefinition,
    AttributeDefinition,
    VersionedIdentifier,
    DataSourceEntry
)

class AttributeDataSourceOptionSerializer(serializers.ModelSerializer):
    """序列化一个属性的可选项 (例如: 附魔ID 'minecraft:sharpness')"""
    # 我们把 game_value 作为 "value"，把 entry.name 作为 "label"
    value = serializers.CharField(source='game_value')
    label = serializers.CharField(source='entry.name')

    class Meta:
        model = VersionedIdentifier
        fields = ['value', 'label']


class AttributeDefinitionSerializer(serializers.ModelSerializer):
    """序列化属性定义，并包含其所有可选项"""
    # 这个字段将动态地填充该属性所有可用的选项
    options = serializers.SerializerMethodField()

    class Meta:
        model = AttributeDefinition
        fields = ['key', 'connector', 'value_format', 'value_source', 'options']

    def get_options(self, obj):
        """
        这是核心逻辑：如果一个属性有数据源，
        我们就根据API请求的version，去查找所有有效的选项。
        """
        # 从视图的上下文(context)中获取当前请求的目标版本
        version = self.context.get('version')
        if not version or not obj.value_source:
            return []
        
        # 找到所有属于这个数据源，并且版本匹配的标识符
        identifiers = VersionedIdentifier.objects.filter(
            entry__source=obj.value_source,
            min_version__lte=version,
            max_version__gte=version
        ).select_related('entry')

        # 用上面的序列化器格式化这些选项
        return AttributeDataSourceOptionSerializer(identifiers, many=True).data


class StructureDefinitionSerializer(serializers.ModelSerializer):
    """序列化一个完整的、带版本信息的结构定义"""
    attributes = AttributeDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = StructureDefinition
        fields = [
            'name', 'min_version', 'max_version', 'header', 'connector',
            'list_start', 'list_end', 'entry_delimiter', 'entry_start', 'entry_end',
            'attributes'
        ]

class ComponentSerializer(serializers.ModelSerializer):
    """序列化一个顶层组件，用于列表展示"""
    class Meta:
        model = Component
        fields = ['name', 'component_key']