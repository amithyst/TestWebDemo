from django.db import models

# ==============================================================================
# 阶段一：数据源模型 (这部分保持不变，依然完美)
# ==============================================================================

class DataSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class DataSourceEntry(models.Model):
    source = models.ForeignKey(DataSource, related_name='entries', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    class Meta:
        unique_together = ('source', 'name')
    def __str__(self): return f"{self.source.name} - {self.name}"

class VersionedIdentifier(models.Model):
    entry = models.ForeignKey(DataSourceEntry, related_name='identifiers', on_delete=models.CASCADE)
    min_version = models.CharField(max_length=20)
    max_version = models.CharField(max_length=20)
    game_value = models.CharField(max_length=255)
    def __str__(self): return f"{self.entry.name} ({self.min_version}-{self.max_version}): {self.game_value}"


# ==============================================================================
# 阶段二：版本化的组件结构模型 (这是关键的修改)
# ==============================================================================

class Component(models.Model):
    """
    代表一个抽象的组件概念，用于分组。
    例如：'附魔', '属性', '药水效果'。
    """
    name = models.CharField(max_length=100, unique=True, help_text="组件的通用名称")
    component_key = models.CharField(max_length=100, unique=True, help_text="用于代码调用的唯一键")

    def __str__(self):
        return self.name

class StructureDefinition(models.Model):
    """
    【核心】定义了某个组件在特定版本范围内的完整NBT结构。
    """
    component = models.ForeignKey(Component, related_name='structures', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="便于识别的结构名称, e.g., '附魔 (JSON格式)'")
    min_version = models.CharField(max_length=20)
    max_version = models.CharField(max_length=20)

    # NBT 结构定义 (这些字段现在属于这里)
    header = models.CharField(max_length=100)
    connector = models.CharField(max_length=10, default=':')
    list_start = models.CharField(max_length=10, blank=True)
    list_end = models.CharField(max_length=10, blank=True)
    entry_delimiter = models.CharField(max_length=10, blank=True, default=',')
    entry_start = models.CharField(max_length=10, blank=True)
    entry_end = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ('component', 'min_version', 'max_version')

    def __str__(self):
        return f"{self.component.name} ({self.min_version}-{self.max_version})"

class AttributeDefinition(models.Model):
    """
    属性的定义，现在从属于一个具体的、带版本的结构。
    """
    structure = models.ForeignKey(StructureDefinition, related_name='attributes', on_delete=models.CASCADE)
    key = models.CharField(max_length=100, blank=True)
    connector = models.CharField(max_length=10, default=':')
    value_format = models.CharField(max_length=100, default='{value}')
    value_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.structure} - Attr: {self.key or 'Value'}"