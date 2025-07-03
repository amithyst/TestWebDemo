from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    DataSource,
    DataSourceEntry,
    VersionedIdentifier,
    Component,
    StructureDefinition,
    AttributeDefinition
)

# --- 为了在后台中更好地展示嵌套关系，我们使用StackedInline ---

class VersionedIdentifierInline(admin.StackedInline):
    """在DataSourceEntry的编辑页面中，直接内联显示其所有版本的标识符"""
    model = VersionedIdentifier
    extra = 1  # 默认显示1个额外的空行供添加
    ordering = ('-min_version',) # 按版本号倒序排列

class AttributeDefinitionInline(admin.StackedInline):
    """在StructureDefinition的编辑页面中，直接内联显示其所有属性定义"""
    model = AttributeDefinition
    extra = 1
    fk_name = "structure"

class StructureDefinitionInline(admin.StackedInline):
    """在Component的编辑页面中，直接内联显示其所有的结构定义"""
    model = StructureDefinition
    extra = 0
    ordering = ('-min_version',)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(DataSourceEntry)
class DataSourceEntryAdmin(admin.ModelAdmin):
    """数据概念后台，集成了版本标识符的内联编辑"""
    list_display = ('name', 'source')
    list_filter = ('source',)
    search_fields = ('name',)
    inlines = [VersionedIdentifierInline]


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    """组件概念后台，集成了结构定义的内联编辑"""
    list_display = ('name', 'component_key')
    search_fields = ('name', 'component_key')
    inlines = [StructureDefinitionInline]


@admin.register(StructureDefinition)
class StructureDefinitionAdmin(admin.ModelAdmin):
    """结构定义后台，这是您未来最常维护的地方"""
    list_display = ('__str__', 'component', 'min_version', 'max_version')
    list_filter = ('component',)
    search_fields = ('name', 'component__name')
    ordering = ('component', '-min_version')
    inlines = [AttributeDefinitionInline]


# 我们通常不需要直接编辑VersionedIdentifier或AttributeDefinition，
# 因为它们通过内联方式在父模型中管理更方便，但为了完整性，也注册它们。
@admin.register(VersionedIdentifier)
class VersionedIdentifierAdmin(admin.ModelAdmin):
    list_display = ('entry', 'min_version', 'max_version', 'game_value')
    search_fields = ('entry__name', 'game_value')
    # 建议在生产环境中将此模型的直接编辑权限移除或设为只读

@admin.register(AttributeDefinition)
class AttributeDefinitionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'key', 'value_source')
    # 建议在生产环境中将此模型的直接编辑权限移除或设为只读