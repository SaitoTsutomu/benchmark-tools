import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from core.admin import GroupAdmin, ResultAdmin
from core.models import Group, Item, LlmModel, Result


@pytest.mark.django_db
def test_result_admin_summary_averages_duplicate_records_per_group_item_llm() -> None:
    """重複キーを平均化してからLLMサマリー集計されることを検証する"""
    # Arrange
    group = Group.objects.create(name="group-1")
    item1 = Item.objects.create(name="item-1", problem="q1", answer="a1")
    item2 = Item.objects.create(name="item-2", problem="q2", answer="a2")
    llm_model = LlmModel.objects.create(
        name="model-a",
        base_url="https://example.com/v1",
        api_key_name="DUMMY_API_KEY",
    )

    Result.objects.create(group=group, item=item1, llm_model=llm_model, result="ok", exec_time=1.0, judge=True)
    Result.objects.create(group=group, item=item1, llm_model=llm_model, result="ng", exec_time=3.0, judge=False)
    Result.objects.create(group=group, item=item2, llm_model=llm_model, result="ok", exec_time=5.0, judge=True)
    admin_instance = ResultAdmin(Result, AdminSite())

    # Act
    summary_rows = admin_instance.summary_by_llm(Result.objects.all())

    # Assert
    assert len(summary_rows) == 1
    summary = summary_rows[0]
    assert summary["label"] == "model-a"
    assert summary["total"] == Item.objects.count()
    assert summary["success"] == pytest.approx(1.5)
    assert summary["accuracy"] == pytest.approx(75.0)
    assert summary["avg_exec_time"] == pytest.approx(3.5)


@pytest.mark.django_db
def test_group_admin_display_run_links_to_run_benchmark_view() -> None:
    """実行リンクが単体ベンチマーク実行URLを指すことを検証する"""
    group = Group.objects.create(name="group-1")

    # Act
    html = str(GroupAdmin.display_run(group))

    # Assert
    url = reverse("admin:core_group_run_benchmark", args=(group.pk,))
    assert f'href="{url}"' in html
    assert ">実行</a>" in html
