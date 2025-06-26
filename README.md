# 目前问题（没有就是无）

烟火组件 在 表单编辑界面 只能删除，无法添加（不管是随机颜色还是指定颜色，或者说保存后添加会失效，无法存入数据库）。在admin界面功能完整。

# 常用命令

`pip install django==5.2`

`python manage.py runserver`

```bash
git remote add origin https://github.com/amithyst/TestWebDemo.git
git add .
git commit -m "更新"
git push -u origin master
#
```

切换到根目录创建文件夹**djangotutorial后创建**项目

```
django-admin startproject mysite djangotutorial
```


```python
git restore .
git clean -fd
git pull origin master
#
```


```python
python manage.py makemigrations
python manage.py migrate
#
```


## 导入数据

```python
python manage.py import_components enchantments.json
python manage.py import_components attributes.json
python manage.py import_components effects.json
python manage.py import_components materials.json
python manage.py import_components item_types.json



```

# 导出依赖

#### 第 1 步：安装 `pip-tools`

首先，您需要在您的虚拟环境中安装这个工具。

**Bash**

```
pip install pip-tools
```

#### 第 2 步：创建 `requirements.in` 文件

在您的项目根目录下，手动创建一个名为 `requirements.in` 的文件。根据您之前的上下文，您的项目似乎需要以下这些库。将它们写入文件：

**`requirements.in`**

```
django
selenium
```

**关键点**：您不需要在这里写版本号，`pip-compile` 会自动找出最新的兼容版本。您也不需要写 `jinja2` 或 `click`，因为它们是 `flask` 的子依赖，`pip-compile` 会自动处理。

#### 第 3 步：运行 `pip-compile` 生成 `requirements.txt`

现在，在您的终端中（确保在项目根目录下），运行以下命令：

**Bash**

```
pip-compile requirements.in
```

运行后，您会看到 `pip-compile` 开始解析依赖。
