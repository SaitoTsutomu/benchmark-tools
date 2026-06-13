from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from core.benchmark import run_group_benchmark
from core.models import Group, GroupItem, GroupLlmModel, Item, LlmModel, Result


@pytest.fixture
def group() -> Group:
    """ベンチマーク実行用の基本データを作成する"""
    group = Group.objects.create(name="group-1")
    item = Item.objects.create(name="item-1", problem="1+1は?", answer="2")
    llm_model = LlmModel.objects.create(
        model="dummy-model",
        base_url="https://example.com/v1",
        api_key_name="DUMMY_API_KEY",
    )
    GroupItem.objects.create(group=group, item=item)
    GroupLlmModel.objects.create(group=group, llm_model=llm_model)
    return group


@pytest.mark.django_db
@patch("core.benchmark.os.getenv", return_value="dummy-key")
@patch("core.benchmark.Runner.run_sync")
def test_run_group_benchmark_creates_results(run_sync_mock: Mock, getenv_mock: Mock, group: Group) -> None:
    """正常系でResultが作成されることを検証する"""
    # Arrange
    run_sync_mock.return_value = SimpleNamespace(final_output="2")

    # Act
    summary = run_group_benchmark([group])

    # Assert
    assert summary.created_results == 1
    assert summary.failed_requests == 0
    assert Result.objects.count() == 1
    assert Result.objects.get().judge is True
    getenv_mock.assert_called()


@pytest.mark.django_db
def test_run_group_benchmark_skips_when_no_models(group: Group) -> None:
    """LLMモデル未紐付け時はスキップされることを検証する"""
    # Arrange
    GroupLlmModel.objects.all().delete()

    # Act
    summary = run_group_benchmark([group])

    # Assert
    assert summary.created_results == 0
    assert summary.failed_requests == 0
    assert Result.objects.count() == 0
