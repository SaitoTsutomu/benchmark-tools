import os
import re
import subprocess  # noqa: S404
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any

from agents import Agent, ModelSettings, Runner, function_tool
from agents.exceptions import AgentsException
from agents.extensions.models.litellm_model import LitellmModel
from litellm.exceptions import AuthenticationError
from openai.types.shared import Reasoning

from core.models import Group, Item, LlmModel, Result

if TYPE_CHECKING:
    from agents import Tool

logger = getLogger(__name__)


@dataclass(slots=True)
class BenchmarkRunSummary:
    """ベンチマーク実行結果"""

    created_results: int
    failed_requests: int


class BenchmarkExecutionError(Exception):
    """ベンチマーク実行時の業務エラー"""


def normalize_text(value: str) -> str:
    """ホワイトスペースを正規化"""
    return " ".join(value.strip().split())


def _resolve_api_key(llm_model: LlmModel) -> str:
    key_name = llm_model.api_key_name.strip()
    if not key_name:
        return ""

    api_key = os.getenv(key_name, "")
    if not api_key:
        msg = f"環境変数 '{key_name}' が未設定のため、モデル '{llm_model.model}' を実行できません"
        raise BenchmarkExecutionError(msg)
    return api_key


@function_tool
def execute_python(code: str) -> str:
    """Pythonコードを実行する"""
    rc, stdout, stderr = run_code(code)
    return f"returncode={rc}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"


def run_single_benchmark(item: Item, llm_model: LlmModel) -> tuple[str, float]:
    """単一ベンチマークを実行し、応答と実行時間を返す"""
    tools: list[Tool] = []
    instructions = "出力は常に解答のみ出力すること。出力に「```python」は不要。"
    if llm_model.can_execute_python:
        tools.append(execute_python)
        instructions = (
            f"作成したPythonコードをツールexecute_pythonで実行しエラーがないかを確認すること。"
            "execute_pythonでは入力データは用意されている。"
            f"{instructions}"
        )
    api_key = _resolve_api_key(llm_model)
    model = LitellmModel(llm_model.model, base_url=llm_model.base_url, api_key=api_key)
    options: dict[str, Any] = {"tools": tools, "instructions": instructions}
    if llm_model.effort:
        # Geminiで確認
        options["model_settings"] = ModelSettings(reasoning=Reasoning(effort=llm_model.effort))
    agent = Agent(name="Assistant", model=model, **options)
    start = perf_counter()
    result = Runner.run_sync(agent, item.problem)
    exec_time = perf_counter() - start
    logger.info("Executed %s %s", item.name, item.title)
    return result.final_output, exec_time


def run_code(code: str) -> tuple[int, str, str]:
    """コード実行"""
    # src/dataをマウントしてdockerから使えるようにする
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "run",
            "-i",
            "--rm",
            "-v",
            f"{Path.cwd()}/data:/app/data:ro",
            "--user",
            "1000:1000",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",  # noqa: S108
            "--network",
            "none",
            "--memory=256m",
            "--cpus=1",
            "--pids-limit=64",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--security-opt=apparmor=docker-default",
            "sandbox",
            "python",
            "-",
        ],
        input=code,
        text=True,
        capture_output=True,
        check=False,
    )
    logger.info("run_code \n--------\n%s\n--------\n", code[:500])
    return result.returncode, result.stdout, result.stderr


def check_judge(answer_code: str, re_output: str, answer: str, result: str) -> bool:
    """判定"""
    if not answer_code and not re_output:
        return answer in normalize_text(result)

    code = re.sub(r"^```(python)?", "", result, flags=re.MULTILINE)
    returncode, actual, stderr = run_code(code)
    if returncode or stderr:
        logger.warning("実行エラー %s %s", returncode, stderr)
        return False

    if re_output:
        return all(re.search(s, actual) for s in re_output.splitlines())

    _, expected, _ = run_code(answer_code)
    return actual == expected


def run_group_benchmark(groups: list[Group]) -> BenchmarkRunSummary:
    """テストグループでベンチマークを実行"""
    created_results = 0
    failed_requests = 0

    for group in groups:
        llm_models = LlmModel.objects.filter(group_llm_models__group=group)
        items = Item.objects.filter(group_items__group=group)
        if not items or not llm_models:
            continue

        for item in items:
            answer = normalize_text(item.answer)
            for llm_model in llm_models:
                result = ""
                exec_time = float("inf")  # 未実行を意味する
                judge = None
                try:
                    result, exec_time = run_single_benchmark(item=item, llm_model=llm_model)
                    judge = check_judge(item.answer_code, item.re_output, answer, result)
                except (AuthenticationError, AgentsException) as e:
                    logger.warning("%s", e)
                    failed_requests += 1
                except Exception:
                    logger.exception("Error")
                    failed_requests += 1
                Result.objects.create(
                    group=group,
                    item=item,
                    llm_model=llm_model,
                    result=result,
                    exec_time=exec_time,
                    judge=judge,
                )
                created_results += 1

    return BenchmarkRunSummary(created_results=created_results, failed_requests=failed_requests)
