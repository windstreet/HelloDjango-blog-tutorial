import re

import markdown
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.text import slugify
from markdown.extensions.toc import TocExtension


def generate_rich_content(value):
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.extra",
            "markdown.extensions.codehilite",
            TocExtension(slugify=slugify),
        ]
    )
    content = md.convert(value)
    m = re.search(r'<div class="toc">\s*<ul>(.*)</ul>\s*</div>', md.toc, re.S)
    toc = m.group(1) if m is not None else ""
    return {"content": content, "toc": toc}


class Category(models.Model):
    """分类"""

    name = models.CharField("分类名", max_length=100)

    class Meta:
        verbose_name = "分类"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Tag(models.Model):
    """标签"""

    name = models.CharField("标签名", max_length=100)

    class Meta:
        verbose_name = "标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Post(models.Model):
    """文章（帖子）

    一篇文章只对应一个分类，但一个分类下可以有多篇文章，即一对多的关联关系（ForeignKey）。
    设定当某个分类被删除时，该分类下全部文章也同时被删除，因此使用 `on_delete=models.CASCADE` 参数，意为级联删除。

    一篇文章可以有多个标签，同一个标签下也可能有多篇文章，即多对多的关联关系（ManyToManyField）。
    设定文章可以没有标签，因此为标签 tags 指定了 blank=True。

    一篇文章只能有一个作者，而一个作者可能会写多篇文章，即一对多的关联关系（ForeignKey）。
    """

    title = models.CharField("标题", max_length=70)
    body = models.TextField("正文")

    created_time = models.DateTimeField("创建时间", default=timezone.now)
    modified_time = models.DateTimeField("修改时间")

    excerpt = models.CharField("摘要", max_length=200, blank=True)

    category = models.ForeignKey(Category, verbose_name="分类", on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag, verbose_name="标签", blank=True)

    author = models.ForeignKey(User, verbose_name="作者", on_delete=models.CASCADE)

    # 新增 views 字段记录阅读量
    views = models.PositiveIntegerField(default=0, editable=False)  # 正整数字段

    class Meta:
        verbose_name = "文章"
        verbose_name_plural = verbose_name
        ordering = ["-created_time"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.modified_time = timezone.now()

        # 首先实例化一个 Markdown 类，用于渲染 body 的文本。
        # 由于摘要并不需要生成文章目录，所以去掉了目录拓展。
        md = markdown.Markdown(
            extensions=["markdown.extensions.extra", "markdown.extensions.codehilite", ]
        )

        # 先将 Markdown 文本渲染成 HTML 文本
        # strip_tags 去掉 HTML 文本的全部 HTML 标签
        # 从文本摘取前 54 个字符赋给 excerpt
        self.excerpt = strip_tags(md.convert(self.body))[:54]

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"pk": self.pk})

    def increase_views(self):
        self.views += 1
        self.save(update_fields=["views"])

    @property
    def toc(self):
        return self.rich_content.get("toc", "")

    @property
    def body_html(self):
        return self.rich_content.get("content", "")

    @cached_property
    def rich_content(self):
        return generate_rich_content(self.body)
