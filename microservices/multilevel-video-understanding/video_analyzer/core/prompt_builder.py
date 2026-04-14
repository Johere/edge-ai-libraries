# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.core.prompt_summary import SummaryPrompt
from video_analyzer.core.prompt_valve_sop import EngineValvesSoPPrompt
from video_analyzer.core.prompt_summary_refrigerator import RefrigeratorMonitorPrompt
from video_analyzer.core.prompt_summary_daily_report import DailyReportPrompt
from video_analyzer.core.prompt_summary_daily_report_en import DailyReportEnPrompt
from video_analyzer.core.prompt_summary_refrigerator_en import RefrigeratorMonitorEnPrompt

# Backward-compatible module-level API
def get_prompt_instance(task: str = "summary") -> BasePrompt:
	"""Factory to get a prompt instance by task name."""
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

	raise ValueError(f"Unsupported prompt task: {task}")


def assign_global_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_global_prompt(**kwargs)


def assign_macro_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_macro_prompt(**kwargs)


def assign_local_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_local_prompt(**kwargs)


def assign_t_minus_prompt(task: str = "summary", **kwargs) -> str:
	return get_prompt_instance(task).assign_t_minus_prompt(**kwargs)
