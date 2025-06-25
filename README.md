# 常用命令

```bash
git remote add origin https://github.com/amithyst/TestWebDemo.git
git add .
git commit -m "更新"
git push -u origin master
```

切换到根目录创建文件夹**djangotutorial后创建**项目

```
django-admin startproject mysite djangotutorial
```

改变模型需要这三步：

* 编辑 `models.py` 文件，改变模型。
* 运行 [`python manage.py makemigrations`](https://docs.djangoproject.com/zh-hans/5.2/ref/django-admin/#django-admin-makemigrations) 为模型的改变生成迁移文件。
* 运行 [`python manage.py migrate`](https://docs.djangoproject.com/zh-hans/5.2/ref/django-admin/#django-admin-migrate) 来应用数据库迁移。
* ```python
  python manage.py makemigrations
  python manage.py migrate
  ```

## 导入数据

```python
python manage.py import_components Enchantment MC_command\json_data\enchantments.json
python manage.py import_components AttributeType MC_command\json_data\attributes.json
```

# 项目结构
