# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
Prompt templates for smart-home child-safety video summarization.

Use case: home camera clip analysis where the primary goal is to flag
potentially dangerous child behaviors (knife/剪刀/打火机 handling, climbing
furniture/window, rough falls, jumping on sofa, etc.) while distinguishing
normal play. Local prompts emphasize per-chunk hazard details; macro/global
prompts aggregate incidents across time with special attention to the most
severe event in the window.
"""
from video_analyzer.prompts.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME


# Global summary prompt for the entire video
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
GLOBAL_PROMPT = '''
##任务:
汇总所有子片段的安全判断，输出整段视频的最终安全评估。
用户提问: {question}

##汇总规则:
- 如果任一子片段为critical，整体为critical
- 如果任一子片段为warn（且无critical），整体为warn
- 否则为info

##输出格式（严格遵守，只输出以下4行）:
SEVERITY: critical 或 warn 或 info
EVENT: 最严重事件的短语描述
COUNT: 危险事件总次数（info事件不计）
DESC: 2-3句话概括视频中出现的所有儿童活动和危险事件

##待总结内容:
以下是视频各子部分的总结。
每个子部分用分隔符 ">|<" 分开。
每个子部分总结会以其相对于完整视频的起止时间开头。
'''


# Macro chunk prompt for summarizing a group of micro chunks
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
MACRO_CHUNK_PROMPT = '''
##任务:
汇总以下子片段的安全判断结果，输出该时段内的最高严重度事件。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##汇总规则:
- 如果任一子片段为critical，则整段为critical
- 如果任一子片段为warn（且无critical），则整段为warn
- 否则为info

##输出格式（严格遵守，只输出以下3行）:
SEVERITY: critical 或 warn 或 info
EVENT: 该时段最严重事件的短语描述
DESC: 一句话概括该时段儿童活动

##待总结内容:
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
每个子部分用分隔符 ">|<" 分开。
'''


# Local prompt for summarizing a single micro chunk
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
LOCAL_PROMPT = '''
##任务:
你是一个儿童安全监控AI。分析这段家庭摄像头片段，判断儿童是否有危险行为。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##严重度定义（必须严格按此判断）:
critical — 以下任一情况立即判定:
  - 手持或玩弄刀具、剪刀（即使看起来像在做手工）
  - 手持或玩弄打火机、火柴、接近灶台火源
  - 攀爬窗台、阳台栏杆、站在窗边椅子上够窗户
  - 剧烈摔倒（身体离地后撞击地面）

warn — 以下任一情况:
  - 在沙发、床、桌面上蹦跳或从上面跳下
  - 独自爬上高凳、桌面、柜子
  - 快跑中绊倒或撞到家具
  - 拉扯电线、触碰插座

info — 没有上述任何危险行为:
  - 坐着看书、吃饭、玩玩具、看电视、正常走动

##关键判断原则:
- 宁可误报，不可漏报。如果不确定是否危险，选择更高的严重度
- 不要因为儿童看起来平静就忽略手中的危险物品
- 摔倒只需要看到身体失去平衡倒地，不需要等后续反应
- 儿童手中拿着剪刀即使在正常剪纸也判定为critical（幼儿不应持有利器）

##输出格式（严格遵守，只输出以下3行）:
SEVERITY: critical 或 warn 或 info
EVENT: 用一个短语描述（如：玩剪刀、攀爬窗台、沙发蹦跳、正常看书）
DESC: 一句话描述画面中儿童的具体动作

##禁止事项:
- 不要输出JSON格式
- 不要加markdown符号或方括号
- 不要写分析过程或逐条排查
- 只输出SEVERITY、EVENT、DESC三行，无其他内容
'''


# Previous context prompt for providing context from previous chunk
T_MINUS_1_PROMPT = '''
##上下文（前{dur}秒的判断结果，仅供参考，不要复制到输出中）:
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
{past_summary}

注意：根据上一片段的上下文，独立判断当前片段的SEVERITY。如果上一片段的危险行为在当前片段仍在继续，严重度不应降低。
'''


class SmartHomeChildSafetyPrompt(BasePrompt):
	TASK_NAME: str = TASKNAME.CHILD_SAFETY_MONITOR.value

	@staticmethod
	def _remove_user_prompt_line(lines):
		return [ln for ln in lines if not ln.strip().startswith('用户提问:')]

	def assign_global_prompt(self, **kwargs) -> str:
		template = GLOBAL_PROMPT
		q = kwargs.get('question', '')
		rendered = self._render_validated(
			template,
			kwargs,
			optional_fields={"question"},
		)
		lines = rendered.splitlines()
		if not str(q).strip():
			lines = self._remove_user_prompt_line(lines)
		return "\n".join(lines) + "\n"

	def assign_macro_prompt(self, **kwargs) -> str:
		template = MACRO_CHUNK_PROMPT
		q = kwargs.get('question', '')
		rendered = self._render_validated(
			template,
			kwargs,
			optional_fields={"question"},
		)
		lines = rendered.splitlines()
		if not str(q).strip():
			lines = self._remove_user_prompt_line(lines)
		return "\n".join(lines) + "\n"

	def assign_local_prompt(self, **kwargs) -> str:
		template = LOCAL_PROMPT
		q = kwargs.get('question', '')
		rendered = self._render_validated(
			template,
			kwargs,
			optional_fields={"question"},
		)
		lines = rendered.splitlines()
		if not str(q).strip():
			lines = self._remove_user_prompt_line(lines)
		return "\n".join(lines) + "\n"

	def assign_t_minus_prompt(self, **kwargs) -> str:
		return self._render_validated(
			T_MINUS_1_PROMPT,
			kwargs,
			optional_fields=set(),
		)


if __name__ == "__main__":
	from video_analyzer.utils.summarization_utils import redact_base64

	cp = SmartHomeChildSafetyPrompt()

	global_kwargs = {"question": "请汇总今日出现的儿童危险行为"}
	global_kwargs_minimal = {}

	macro_kwargs = {
		"question": "请汇总这一时段儿童的安全状况",
		"st_tm": 0,
		"end_tm": 60,
	}

	local_kwargs = {
		"question": "请判断儿童是否有危险行为",
		"st_tm": 10,
		"end_tm": 20,
	}
	local_kwargs_minimal = {"st_tm": 10, "end_tm": 20}

	tminus_kwargs = {
		"dur": 10,
		"st_tm": 0,
		"end_tm": 10,
		"past_summary": "一名穿红色连衣裙的女孩在沙发上蹦跳，成人在旁但未制止。",
	}

	print("=== GLOBAL (with question) ===\n")
	print(cp.assign_global_prompt(**global_kwargs))

	print("\n=== GLOBAL (minimal) ===\n")
	print(cp.assign_global_prompt(**global_kwargs_minimal))

	print("\n=== MACRO ===\n")
	print(cp.assign_macro_prompt(**macro_kwargs))

	print("\n=== LOCAL (with question) ===\n")
	print(cp.assign_local_prompt(**local_kwargs))

	print("\n=== LOCAL (minimal) ===\n")
	print(cp.assign_local_prompt(**local_kwargs_minimal))

	print("\n=== T-MINUS ===\n")
	print(cp.assign_t_minus_prompt(**tminus_kwargs))
