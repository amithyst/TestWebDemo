# mc_commands/models.py

from django.db import models
from django.contrib.auth.models import User

# ==============================================================================
# 1. 基础与版本控制模型 (无变化)
# ==============================================================================

class MinecraftVersion(models.Model):
    """存储支持的 Minecraft 版本。"""
    version_number = models.CharField(max_length=20, unique=True, help_text="例如 '1.20.1' 或 '1.21.4'")
    ordering_id = models.PositiveIntegerField(unique=True, help_text="用于排序和比较的版本整数ID, 例如 12001 代表 1.20.1")

    class Meta:
        ordering = ['ordering_id']

    def __str__(self):
        return self.version_number

# ==============================================================================
# 2. 静态游戏数据模型 (带有版本范围)
# ==============================================================================

class VersionedItem(models.Model):
    """一个抽象基类，为所有需要版本控制的静态游戏数据提供通用字段。"""
    min_version = models.ForeignKey(
        MinecraftVersion, on_delete=models.PROTECT, related_name='+',
        blank=True, null=True, help_text="该项目有效的最低版本 (留空表示无限制)"
    )
    max_version = models.ForeignKey(
        MinecraftVersion, on_delete=models.PROTECT, related_name='+',
        blank=True, null=True, help_text="该项目有效的最高版本 (留空表示无限制)"
    )

    class Meta:
        abstract = True

class BaseItem(VersionedItem):
    """存储所有可用的基础物品及其版本范围"""
    item_id = models.CharField(max_length=100, help_text="Minecraft 的物品ID, 例如 'minecraft:diamond_sword'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Diamond Sword'")

    def __str__(self):
        return f"{self.name} ({self.item_id})"

class Enchantment(VersionedItem):
    """存储所有可用的附魔类型及其版本范围"""
    enchant_id = models.CharField(max_length=100, help_text="附魔ID, 例如 'minecraft:sharpness'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Sharpness'")
    max_level = models.PositiveIntegerField(default=127, help_text="附魔的最大等级, 例如 Sharpness 的最大等级是 127")

    def __str__(self):
        return self.name

class PotionEffectType(VersionedItem):
    """存储所有药水效果类型及其版本范围"""
    effect_id = models.CharField(max_length=100, help_text="药水效果ID, 例如 'minecraft:speed'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Speed'")
    
    def __str__(self):
        return self.name

# --- 新增的静态数据模型 ---
class AttributeType(VersionedItem):
    """存储所有可用的属性类型及其版本范围"""
    attribute_id = models.CharField(max_length=100, help_text="属性ID, 例如 'generic.attack_damage'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Generic Attack Damage'")

    def __str__(self):
        return self.name

# ==============================================================================
# 3. 核心用户创建内容模型 (无变化)
# ==============================================================================

class GeneratedCommand(models.Model):
    """用户创建的一个完整的物品命令配置。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commands")
    title = models.CharField(max_length=100, help_text="为这个命令配置起一个名字，方便查找")
    target_version = models.ForeignKey(MinecraftVersion, on_delete=models.PROTECT, help_text="命令生成的目标 Minecraft 版本")
    base_item = models.ForeignKey(BaseItem, on_delete=models.PROTECT, help_text="该命令的基础物品")
    custom_name = models.CharField(max_length=255, blank=True, null=True, help_text="物品在游戏中的自定义名称 (支持JSON文本)")
    lore = models.TextField(blank=True, null=True, help_text="物品的描述文字 (支持JSON文本), 每行用 \\n 分隔")
    count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"'{self.title}' for v{self.target_version} by {self.user.username}"


# ==============================================================================
# 4. 物品组件模型 (与 GeneratedCommand 关联)
# ==============================================================================

class AppliedEnchantment(models.Model):
    """连接 GeneratedCommand 和 Enchantment，并存储附魔等级"""
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="enchantments")
    enchantment = models.ForeignKey(Enchantment, on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('command', 'enchantment')

# --- 修正后的模型 ---
class AppliedAttribute(models.Model):
    """
    存储应用到物品上的属性修改器。
    替代了原先的 AttributeModifier 模型。
    """
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="attributes")
    attribute = models.ForeignKey(AttributeType, on_delete=models.CASCADE) 
    amount = models.FloatField()
    operation = models.IntegerField(choices=[(0, "add_value"), (1, "add_multiplied_base"), (2, "add_multiplied_total")], default=0)
    slot = models.CharField(max_length=20, choices=[("any", "Any"), ("mainhand", "Main Hand"), ("offhand", "Off Hand"), ("head", "Head"), ("chest", "Chest"), ("legs", "Legs"), ("feet", "Feet")], default="any")
    
    # --- 这里是关键改动 ---
    modifier_name = models.CharField(
        max_length=100,
        blank=True,  # 允许该字段在表单中为空
        null=True,   # 允许数据库中该字段为 NULL
        help_text="[重要] 仅用于 1.20.4 及更早版本。1.20.5+ 版本已废弃此字段。"
    )

    def __str__(self):
        # 增加一个更有用的字符串表示
        return f"{self.attribute.name} on {self.command.title}"

class AppliedPotionEffect(models.Model):
    """存储应用于物品的自定义药水效果"""
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="potion_effects")
    effect = models.ForeignKey(PotionEffectType, on_delete=models.CASCADE)
    amplifier = models.PositiveIntegerField(default=0, help_text="效果等级, 从0开始 (0=I, 1=II)")
    duration = models.PositiveIntegerField(default=600, help_text="持续时间 (单位: ticks, 20 ticks = 1s)")
    show_particles = models.BooleanField(default=True)
    is_ambient = models.BooleanField(default=False)

class WrittenBookContent(models.Model):
    """存储成书 (`minecraft:written_book`) 的内容"""
    command = models.OneToOneField(GeneratedCommand, on_delete=models.CASCADE, related_name="book_content")
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=50)
    pages = models.TextField(help_text="书本内容，存储为 JSON 字符串数组")