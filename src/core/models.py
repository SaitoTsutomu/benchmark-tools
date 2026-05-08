from typing import ClassVar

from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """タイムスタンプ共通基底"""

    created_at = models.DateTimeField(default=timezone.now, null=False)
    updated_at = models.DateTimeField(default=timezone.now, null=False)

    class Meta:
        abstract = True

    def save(self, *args: object, **kwargs: object) -> None:
        """時刻を更新する"""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class LlmModel(TimestampedModel):
    """LLMモデル"""

    model = models.CharField("モデル名", max_length=255, unique=True)
    base_url = models.URLField("URL")
    api_key_name = models.CharField("APIキーの環境変数名", max_length=255, blank=True)
    can_parallel = models.BooleanField("並列実行可能か", default=False)

    class Meta:
        verbose_name = verbose_name_plural = "LLMモデル"
        constraints: ClassVar[list[models.UniqueConstraint]] = [
            models.UniqueConstraint(
                fields=["model", "base_url"],
                name="uniq_llmmodel_model_base_url",
            )
        ]

    def __str__(self) -> str:
        return self.model


class Item(TimestampedModel):
    """テスト項目"""

    name = models.CharField("名前", max_length=255, unique=True)
    problem = models.TextField("問題")
    answer = models.TextField("正解")

    class Meta:
        verbose_name = verbose_name_plural = "テスト項目"

    def __str__(self) -> str:
        return self.name


class Group(TimestampedModel):
    """テストグループ"""

    name = models.CharField("名前", max_length=255, unique=True)

    class Meta:
        verbose_name = verbose_name_plural = "テストグループ"

    def __str__(self) -> str:
        return self.name


class GroupItem(TimestampedModel):
    """テストグループとテスト項目"""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="group_items", verbose_name="テスト項目")
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="group_items", verbose_name="テストグループ"
    )

    class Meta:
        constraints: ClassVar[list[models.UniqueConstraint]] = [
            models.UniqueConstraint(
                fields=["item", "group"],
                name="uniq_groupitem_item_group",
            )
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.item.name}"


class Result(TimestampedModel):
    """テスト結果"""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="results", verbose_name="テストグループ")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="results", verbose_name="テスト項目")
    llm_model = models.ForeignKey(LlmModel, on_delete=models.CASCADE, related_name="results", verbose_name="LLMモデル")
    result = models.CharField("解答", max_length=255)
    judge = models.BooleanField("判定結果")

    class Meta:
        verbose_name = verbose_name_plural = "テスト結果"

    def __str__(self) -> str:
        return f"{self.group.name} {self.item.name} {self.llm_model.model.split('/')[-1]}"
