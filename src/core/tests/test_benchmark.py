from unittest.mock import Mock, patch

import pytest

from core.benchmark import BenchmarkExecutionError, run_group_benchmark
from core.models import Group, GroupItem, Item, LlmModel, Result


@pytest.fixture
def group() -> Group:
    """ベンチマーク実行用の基本データを作成する"""
    group = Group.objects.create(name="group-1")
    item = Item.objects.create(name="item-1", problem="1+1は?", answer="2")
    GroupItem.objects.create(group=group, item=item)
    LlmModel.objects.create(
        model="dummy-model",
        base_url="https://example.com/v1",
        api_key_name="DUMMY_API_KEY",
    )
    return group


@pytest.mark.django_db
@patch("core.benchmark.os.getenv", return_value="dummy-key")
@patch("core.benchmark.OpenAI")
def test_run_group_benchmark_creates_results(openai_mock: Mock, _getenv_mock: Mock, group: Group) -> None:
    """正常系でResultが作成されることを検証する"""
    message = Mock()
    message.content = "2"

    choice = Mock()
    choice.message = message

    completion = Mock()
    completion.choices = [choice]

    openai_mock.return_value.chat.completions.create.return_value = completion

    summary = run_group_benchmark([group])

    assert summary.created_results == 1
    assert summary.failed_requests == 0
    assert Result.objects.count() == 1
    assert Result.objects.get().judge is True


@pytest.mark.django_db
@patch("core.benchmark.os.getenv", return_value="")
def test_run_group_benchmark_raises_when_api_key_missing(_getenv_mock: Mock, group: Group) -> None:
    """APIキー未設定時に業務エラーとなることを検証する"""
    with pytest.raises(BenchmarkExecutionError):
        run_group_benchmark([group])

    assert Result.objects.count() == 0


@pytest.mark.django_db
def test_run_group_benchmark_raises_when_no_models(group: Group) -> None:
    """LLMモデル未登録時に業務エラーとなることを検証する"""
    LlmModel.objects.all().delete()

    with pytest.raises(BenchmarkExecutionError):
        run_group_benchmark([group])
