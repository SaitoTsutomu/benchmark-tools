from typing import ClassVar

from django.db import models


class LlmModel(models.Model):
    """LLMモデル"""

    model = models.CharField("モデル名", max_length=255)
    base_url = models.URLField()
    api_key_name = models.CharField(max_length=255)
    can_parallel = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list[models.UniqueConstraint]] = [
            models.UniqueConstraint(
                fields=["model", "base_url"],
                name="uniq_llmmodel_model_base_url",
            )
        ]

    def __str__(self) -> str:
        return self.model


class Item(models.Model):
    """テスト項目"""

    name = models.CharField(max_length=255, unique=True)
    problem = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Group(models.Model):
    """テストグループ"""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class GroupItem(models.Model):
    """テストグループとテスト項目"""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="group_items")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="group_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list[models.UniqueConstraint]] = [
            models.UniqueConstraint(
                fields=["item", "group"],
                name="uniq_groupitem_item_group",
            )
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.item.name}"


class Result(models.Model):
    """テスト結果"""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="results")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="results")
    llm_model = models.ForeignKey(LlmModel, on_delete=models.CASCADE, related_name="results")
    judge = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"group={self.group.name}, item={self.item.name}, model={self.llm_model.model}, judge={self.judge}"
