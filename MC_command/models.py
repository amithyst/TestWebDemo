# mc_commands/models.py
import uuid # <--- 在文件顶部添加此行
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
        verbose_name = "版本"
        verbose_name_plural = "[版本]"

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
        verbose_name_plural = "材质"
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
    # --- 在这里进行修改 ---
    display_name = models.CharField(
        max_length=50,
        help_text="用于显示的名称, e.g., '剑'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )

    class Meta:
        verbose_name = "物品类型"
        verbose_name_plural = "物品类型"
        ordering = ['display_name']

    def __str__(self):
        # 同样，如果显示名称为空，则返回系统名称
        return self.display_name or self.system_name

class BaseItem(VersionedItem):
    """基础物品，其核心属性由材质和类型自动生成"""
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, null=True, blank=True,
        help_text="物品的材质", db_index=True
    )
    item_type = models.ForeignKey(
        ItemType, on_delete=models.PROTECT, null=True, blank=True,
        help_text="物品的基础类型", db_index=True
    )

    # 这两个字段将由 save() 方法自动填充，并且不可编辑
    item_id = models.CharField(
        max_length=100, unique=True, editable=False,
        help_text="自动生成的 Minecraft ID"
    )
    name = models.CharField(
        max_length=100, editable=False,
        help_text="自动生成的显示名称"
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
        verbose_name = "基础物品"
        verbose_name_plural = "基础物品"
        unique_together = ('material', 'item_type')
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        # 验证：材质和物品类型不能同时为空
        if not self.material and not self.item_type:
            raise ValidationError("材质 (Material) 和物品类型 (ItemType) 不能同时为空。")

    def _generate_name_and_id(self):
        """根据材质和类型生成名称和ID的内部逻辑"""
        material_dn = self.material.display_name if self.material else ""
        material_sn = self.material.system_name if self.material else ""
        
        type_dn = self.item_type.display_name if self.item_type else ""
        type_sn = self.item_type.system_name if self.item_type else ""

        # 生成显示名称 (name)
        if material_dn and type_dn:
            self.name = f"{material_dn} {type_dn}"
        else:
            self.name = material_dn or type_dn

        # 生成系统ID (item_id)
        # 规则: material_sn + "_" + type_sn (如果都有)
        # 例如: diamond_sword, iron_ingot, diamond, trident
        if material_sn and type_sn:
            # 特殊规则：如果物品类型本身就包含材质（如 netherite_sword），则以物品类型为准
            if material_sn in type_sn:
                 base_id = type_sn
            else:
                 base_id = f"{material_sn}_{type_sn}"
        else:
            base_id = material_sn or type_sn
        
        self.item_id = f"minecraft:{base_id}"


    def save(self, *args, **kwargs):
        # 在保存前，自动生成 name 和 item_id
        self._generate_name_and_id()
        # 调用父类的save方法，完成保存
        super().save(*args, **kwargs)

class Enchantment(VersionedItem):
    """存储所有可用的附魔类型及其版本范围"""
    enchant_id = models.CharField(max_length=100, help_text="附魔ID, 例如 'minecraft:sharpness'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Sharpness'")
    max_level = models.PositiveIntegerField(default=127, help_text="附魔的最大等级, 例如 Sharpness 的最大等级是 127")
    enchant_type = models.CharField(
        max_length=50,help_text="附魔类型, 例如 'weapon', 'armor', 'fishing_rod', 'trident' 等",
        choices=[
            ('weapon', '武器'),
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
        verbose_name_plural = "附魔效果"
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
        verbose_name_plural = "药水效果"
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
        verbose_name_plural = "属性效果"
        ordering = ['name']

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
    
    class Meta:
        verbose_name = "物品配置"
        verbose_name_plural = "<完整物品配置>"


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