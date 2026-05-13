# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from video_analyzer.prompts.prompt_base import BasePrompt
from video_analyzer.prompts.prompt_summary import SummaryPrompt
from video_analyzer.prompts.prompt_valve_sop import EngineValvesSoPPrompt
from video_analyzer.prompts.prompt_summary_refrigerator import RefrigeratorMonitorPrompt
from video_analyzer.prompts.prompt_summary_daily_report import DailyReportPrompt
from video_analyzer.prompts.prompt_summary_daily_report_en import DailyReportEnPrompt
from video_analyzer.prompts.prompt_summary_refrigerator_en import RefrigeratorMonitorEnPrompt


# Backward-compatible module-level API
def get_prompt_instance(task: str = "summary") -> BasePrompt:
	"""Factory to get a prompt instance by task name.

	Falls back to the runtime registry (dynamic video summary tasks) when the
	name doesn't match any built-in. Built-ins take precedence.
	"""
	task = (task or "").strip().lower()

	if task == SummaryPrompt.TASK_NAME:
		return SummaryPrompt()

	if task == EngineValvesSoPPrompt.TASK_NAME:
		return EngineValvesSoPPrompt()

	if task == RefrigeratorMonitorPrompt.TASK_NAME:
		return RefrigeratorMonitorPrompt()

	if task == DailyReportPrompt.TASK_NAME:
		return DailyReportPrompt()

	if task == DailyReportEnPrompt.TASK_NAME:
		return DailyReportEnPrompt()

	if task == RefrigeratorMonitorEnPrompt.TASK_NAME:
		return RefrigeratorMonitorEnPrompt()

	# Dynamic registry fallback. Lazy import avoids a startup cycle: this module
	# is imported by summarizer which is imported by endpoints which is imported
	# by router (which also imports the registry-backed /v1/tasks handlers).
	from video_analyzer.prompts.prompt_registry import get_registry
	dyn = get_registry().get(task)
	if dyn is not None:
		return dyn

	raise ValueError(f"Unsupported prompt task: {task}")


def assign_global_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_global_prompt(**kwargs)


def assign_macro_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_macro_prompt(**kwargs)


def assign_local_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_local_prompt(**kwargs)


def assign_t_minus_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_t_minus_prompt(**kwargs)
