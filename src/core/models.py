from typing import ClassVar

from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimestampedModel(models.Model):
    """タイムスタンプ共通基底"""

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    def save(self, *args: object, **kwargs: object) -> None:
        """時刻を更新する"""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class Effort(models.TextChoices):
    """Reasoningのeffort"""

    EMPTY = "", ""
    NONE = "none", "None"
    MINIMAL = "minimal", "Minimal"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    XHIGH = "xhigh", "Xhigh"


class LlmModel(TimestampedModel):
    """LLMモデル"""

    name = models.CharField("名前", max_length=255, unique=True)
    model = models.CharField("モデル名", max_length=255)
    description = models.TextField("説明", blank=True)
    base_url = models.URLField("URL", blank=True)
    api_key_name = models.CharField("APIキーの環境変数名", max_length=255, blank=True)
    effort = models.CharField(
        max_length=16,
        choices=Effort,
        default=Effort.EMPTY,
        verbose_name="thinkingレベル",
        help_text="LM Studioでは無効。geminiの場合 https://ai.google.dev/gemini-api/docs/thinking",
    )
    can_execute_python = models.BooleanField(
        "ツール使用可", help_text="Pythonコードを実行できるかどうか", default=False
    )

    class Meta:
        verbose_name = verbose_name_plural = "LLMモデル"

    def __str__(self) -> str:
        return self.name


class Item(TimestampedModel):
    """テスト項目"""

    name = models.CharField("名前", max_length=255, unique=True)
    title = models.CharField("タイトル", max_length=255)
    problem = models.TextField("問題")
    answer_code = models.TextField("正解コード", blank=True, help_text="re_outputより優先")
    re_output = models.TextField("出力(正規表現)", blank=True, help_text="answerより優先")
    answer = models.TextField("正解", blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "テスト項目"
        constraints = (
            models.CheckConstraint(
                condition=~(Q(answer_code="") & Q(answer="")),
                name="answer_code_and_answer_is_not_empty",
            ),
        )

    def __str__(self) -> str:
        return self.title


class Group(TimestampedModel):
    """テストグループ"""

    name = models.CharField("名前", max_length=255, unique=True)
    description = models.TextField("説明", blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "テストグループ"

    def __str__(self) -> str:
        return self.name


class GroupLlmModel(TimestampedModel):
    """テストグループが実施するLLMモデル"""

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="group_llm_models", verbose_name="テストグループ"
    )
    llm_model = models.ForeignKey(
        LlmModel, on_delete=models.CASCADE, related_name="group_llm_models", verbose_name="LLMモデル"
    )

    class Meta:
        constraints: ClassVar[list[models.UniqueConstraint]] = [
            models.UniqueConstraint(
                fields=["group", "llm_model"],
                name="uniq_group_llm_model",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.llm_model.model}"


class GroupItem(TimestampedModel):
    """テストグループが実施するテスト項目"""

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="group_items", verbose_name="テストグループ"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="group_items", verbose_name="テスト項目")

    class Meta:
        constraints: ClassVar[list[models.UniqueConstraint]] = [
            models.UniqueConstraint(
                fields=["group", "item"],
                name="uniq_group_item",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.item.name}"


class Result(TimestampedModel):
    """テスト結果"""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="results", verbose_name="テストグループ")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="results", verbose_name="テスト項目")
    llm_model = models.ForeignKey(LlmModel, on_delete=models.CASCADE, related_name="results", verbose_name="LLMモデル")
    result = models.TextField("解答")
    exec_time = models.FloatField("実行時間")
    judge = models.BooleanField("判定結果", null=True)

    class Meta:
        verbose_name = verbose_name_plural = "テスト結果"

    def __str__(self) -> str:
        return f"{self.group.name} {self.item.name} {self.llm_model.model.split('/')[-1]}"
