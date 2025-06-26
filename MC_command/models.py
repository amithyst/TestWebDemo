# mc_commands/models.py
import uuid # <--- 在文件顶部添加此行
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError # 引入验证错误

# ==============================================================================
# 1. 基础与版本控制模型 (无变化)
# ==============================================================================

class MinecraftVersion(models.Model):
    """存储支持的 Minecraft 版本。"""
    version_number = models.CharField(max_length=20, unique=True, help_text="例如 '1.20.1' 或 '1.21.4'")
    ordering_id = models.PositiveIntegerField(unique=True, help_text="用于排序和比较的版本整数ID, 例如 12001 代表 1.20.1")

    class Meta:
        ordering = ['ordering_id']
        verbose_name = "版本"
        verbose_name_plural = "<1>版本"

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

# --- 新增模型：Material ---

class Material(models.Model):
    """存储物品材质，例如：钻石 (diamond)"""
    system_name = models.CharField(max_length=50, unique=True, help_text="系统内部名称, e.g., 'diamond'"
                                   ,
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
        )
    # --- 在这里进行修改 ---
    display_name = models.CharField(
        max_length=50,
        help_text="用于显示的名称, e.g., '钻石'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )

    class Meta:
        verbose_name = "材质"
        verbose_name_plural = "<💎>材质"
        ordering = ['display_name']

    def __str__(self):
        # 如果显示名称为空，则返回系统名称，避免显示空白
        return self.display_name or self.system_name

class ItemType(models.Model):
    """存储物品基础类型，例如：剑 (sword)"""
    system_name = models.CharField(max_length=50, unique=True, help_text="系统内部名称, e.g., 'sword'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )
    display_name = models.CharField(
        max_length=50,
        help_text="用于显示的名称, e.g., '剑'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )
    function_type = models.CharField(
        max_length=50, help_text="物品的功能分类",
        choices=[
            ('all', '普通物品'),
            ('spawn_egg', '生成蛋'),
            ('potion', '药水(箭/食物)'),
            ('written_book', '成书'),
            ('firework', '烟花火箭'),
        ],default='all', verbose_name="功能类型"
    )

    class Meta:
        verbose_name = "物品类型"
        verbose_name_plural = "<🗡>物品类型"
        ordering = ['display_name']

    def __str__(self):
        # 同样，如果显示名称为空，则返回系统名称
        return self.display_name or self.system_name

class Enchantment(VersionedItem):
    """存储所有可用的附魔类型及其版本范围"""
    enchant_id = models.CharField(max_length=100, help_text="附魔ID, 例如 'minecraft:sharpness'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Sharpness'")
    max_level = models.PositiveIntegerField(default=127, help_text="附魔的最大等级, 例如 Sharpness 的最大等级是 127")
    enchant_type = models.CharField(
        max_length=50,help_text="附魔类型, 例如 'weapon', 'armor', 'fishing_rod', 'trident' 等",
        choices=[
            ('weapon', '武器'),
            ('tool', '工具'),
            ('armor', '盔甲'),
            ('fishing_rod', '钓鱼竿'),
            ('trident', '三叉戟'),
            ('bow', '弓'),
            ('crossbow', '弩'),
            ('all', '杂项'),
            ('helmet', '头盔'),
            ('boots', '靴子'),
        ],
        default='all'
    )
    class Meta:
        verbose_name = "附魔效果"
        verbose_name_plural = "[🔥]附魔效果"
        ordering = ['name']

    def __str__(self):
        return self.name

class PotionEffectType(VersionedItem):
    """存储所有可用的药水效果"""
    effect_id = models.CharField(max_length=100, unique=True, verbose_name="效果ID")
    name = models.CharField(max_length=100, verbose_name="效果名称")
    min_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="最低兼容版本")
    max_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="最高兼容版本")
    
    class Meta:
        verbose_name = "药水效果"
        verbose_name_plural = "[💧]药水效果"
        ordering = ['name']

    def __str__(self):
        return self.name

# --- 新增的静态数据模型 ---
class AttributeType(VersionedItem):
    """存储所有可用的属性类型及其版本范围"""
    attribute_id = models.CharField(max_length=100, help_text="属性ID, 例如 'generic.attack_damage'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Generic Attack Damage'")

    class Meta:
        verbose_name = "属性效果"
        verbose_name_plural = "[💪]属性效果"
        ordering = ['name']

    def __str__(self):
        return self.name
# ==============================================================================
# 3. 核心用户创建内容模型 (已修改)
# ==============================================================================
class GeneratedCommand(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commands")
    title = models.CharField(max_length=100, help_text="为这个命令配置起一个名字，方便查找")
    target_version = models.ForeignKey(MinecraftVersion, on_delete=models.PROTECT, help_text="命令生成的目标 Minecraft 版本")
    material = models.ForeignKey(Material, on_delete=models.PROTECT, null=True, blank=True, help_text="物品的材质")
    item_type = models.ForeignKey(ItemType, on_delete=models.PROTECT, null=True, blank=True, help_text="物品的基础类型")
    custom_name = models.CharField(max_length=255, blank=True, null=True, help_text="物品在游戏中的自定义名称 (支持JSON文本)")
    lore = models.TextField(blank=True, null=True, help_text="物品的描述文字 (支持JSON文本), 每行用 \\n 分隔")
    count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def item_name(self):
        material_dn = self.material.display_name if self.material else ""
        type_dn = self.item_type.display_name if self.item_type else ""
        if material_dn and type_dn:
            return f"{material_dn} {type_dn}"
        return material_dn or type_dn
    
    @property
    def item_id(self):
        material_sn = self.material.system_name if self.material else ""
        type_sn = self.item_type.system_name if self.item_type else ""
        base_id = ""
        if material_sn and type_sn:
            base_id = f"{material_sn}_{type_sn}"
        else:
            base_id = material_sn or type_sn
        return f"minecraft:{base_id}" if base_id else ""

    @property
    def function_type(self):
        if self.item_type:
            return self.item_type.function_type
        return 'all'
    
    def clean(self):
        if not self.material and not self.item_type:
            raise ValidationError("材质 (Material) 和物品类型 (ItemType) 不能同时为空。")
    
    def __str__(self):
        return f"'{self.title}' for v{self.target_version} by {self.user.username}"
    
    class Meta:
        verbose_name = "物品配置"
        verbose_name_plural = "<0>完整物品配置"


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
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, help_text="修饰符的唯一ID，自动生成。")
    
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
    """将一个药水效果应用到一个生成的命令上"""
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="potion_effects", verbose_name="所属命令")
    effect = models.ForeignKey(PotionEffectType, on_delete=models.CASCADE, verbose_name="药水效果")
    amplifier = models.PositiveIntegerField(default=0, help_text="效果等级, 从0开始 (0=I, 1=II)")
    duration = models.PositiveIntegerField(default=600, help_text="持续时间 (单位: ticks, 20 ticks = 1s)")
    is_ambient = models.BooleanField(default=False, help_text="设为True时粒子效果会有信标?")
    show_particles = models.BooleanField(default=True, help_text="是否显示粒子效果")
    show_icon = models.BooleanField(default=True, help_text="是否在HUD中显示效果图标")

    class Meta:
        verbose_name = "应用的药水效果"
        verbose_name_plural = "应用的药水效果"

    def __str__(self):
        return f"{self.command.title} - {self.effect.name} (等级 {self.amplifier})"


class WrittenBookContent(models.Model):
    """存储成书 (`minecraft:written_book`) 的内容"""
    command = models.OneToOneField(GeneratedCommand, on_delete=models.CASCADE, related_name="book_content")
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=50)
    pages = models.TextField(help_text="书本内容，存储为 JSON 字符串数组")


# --- 新增烟火之星模型 ---
class AppliedFireworkExplosion(models.Model):
    """存储烟花爆炸（烟火之星）的详细信息。"""
    SHAPE_CHOICES = [
        (0, '小球型 (Small Ball)'),
        (1, '大球型 (Large Ball)'),
        (2, '星型 (Star-shaped)'),
        (3, '苦力怕型 (Creeper-shaped)'),
        (4, '爆裂型 (Burst)'),
        ('random', '随机形状'),
    ]

    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="firework_explosions")

    # 外观属性
    shape = models.CharField(max_length=10, choices=SHAPE_CHOICES, default=0, verbose_name="形状")
    has_trail = models.BooleanField(default=False, verbose_name="有尾迹")
    has_twinkle = models.BooleanField(default=False, verbose_name="闪烁")

    # 颜色属性
    # 存储颜色为整数列表的JSON字符串, e.g., "[16711680, 255]" (红色, 黄色)
    # 也可存储特殊值 "random"
    colors = models.CharField(max_length=255, default='[]', help_text="JSON格式的颜色整数列表, 或 'random' 表示随机", verbose_name="主颜色")
    fade_colors = models.CharField(max_length=255, default='[]', help_text="JSON格式的淡出颜色整数列表, 或 'random' 表示随机", verbose_name="淡出颜色")

    # 重复属性
    repeat_count = models.PositiveIntegerField(default=1, help_text="此烟火之星在烟花火箭中重复的次数", verbose_name="重复次数")


    class Meta:
        verbose_name = "烟火爆炸效果"
        verbose_name_plural = "烟火爆炸效果"

    def __str__(self):
        return f"{self.command.title} 的烟火之星 - {self.get_shape_display()}"
