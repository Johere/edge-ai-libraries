# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
Prompt templates for refrigerator monitoring video summarization.
Tailored for smart home scenarios: door open/close detection, person identification,
item interaction tracking, and abnormal behavior alerting.
"""
from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME

# Global summary prompt for the entire video
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
GLOBAL_PROMPT = '''
##任务:
你正在分析一段智能家居场景中的冰箱监控视频。请根据以下所有子片段的描述，生成一份连贯的冰箱使用事件摘要。不要提及时间戳。
用户提问: {question}

##指南:
- 以叙事体输出，不要提及具体时间戳（秒或分钟），让摘要读起来像一段完整的描述。
- 统计并报告以下关键指标：冰箱门打开次数、每次开门的大致时长、涉及的不同人物数量。
- 重点描述每次开门事件中取出或放入了哪些物品，物品的类型和特征。
- **重要** 标记异常行为：冰箱门长时间未关闭（超过30秒）、反复快速开关门、深夜时段频繁开门等。
- **重要** 通过衣着、体型等外观特征区分不同人物，保持前后一致的人物指代。
- 不要臆造视频中未出现的内容，严格基于片段描述进行总结。

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
你正在分析一段智能家居场景中的冰箱监控视频片段。请汇总以下子片段描述，按时间线串联事件，保留关键时间戳。
用户提问: {question}

##指南:
- 按时间顺序串联各子片段的事件，合并同一人物的连续操作。
- 突出物品变化：明确记录哪些物品被从冰箱中取出、哪些被放回。
- 如果同一人物在多个子片段中出现，保持一致的人物特征描述（如"穿白色T恤的人"）。
- 注意前面片段出现的物体和场景未必出现在当前片段，不要想当然地认为所有片段都有相同元素。
- **重要** 保留所有与冰箱交互相关的细节，包括门的开关、物品的取放、人物的动作。
- 摘要中不要包含 "[" 或 "]"。

##待总结内容:
以下是视频片段各子部分的总结。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
每个子部分用分隔符 ">|<" 分开。
每个子部分总结会以其相对于完整视频的起止时间开头。
- 输出中不要重复 "开始时间" 和 "结束时间"。
'''

# Local prompt for summarizing a single micro chunk
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
LOCAL_PROMPT = '''
##任务:
你正在分析一段智能家居场景中的冰箱监控视频片段。请详细描述该片段中与冰箱相关的所有活动。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##指南:
- 重点关注以下内容：
  1. 冰箱门状态：门是否打开、关闭、半开，门的开合角度变化。
  2. 物品交互：详细描述从冰箱中取出或放入的每一件物品，包括物品类型（食物、饮料、容器等）、颜色、形状、包装特征。
  3. 冰箱内部：如果冰箱内部可见，描述可见的物品摆放情况。
  4. 人物动作：描述人物在冰箱前的具体动作（弯腰、伸手、翻找、站立等待等）。
- **重要** 输出尽量简洁，包含以上描述的需要点，这些信息将用于后续的事件分析和异常检测。
- 如果画面中出现文字（如食品标签），请以原语言描述并在括号中提供翻译。
- 如果该片段中没有与冰箱相关的活动（如人物仅路过），也请如实描述画面内容。
- 摘要中不要包含 "[" 或 "]"。
- 输出中不要包含 "开始时间" 和 "结束时间"。
'''

# Previous context prompt for providing context from previous chunk
T_MINUS_1_PROMPT = '''
##上下文:
前 {dur} 秒的视频总结放在方括号 [] 中。
**重要** 需要将上一片段的描述视为上下文，并总结接下来的视频片段。
**重要** 不要在输出中复制上一片段的总结。
**重要** 注意上一片段中冰箱门的状态和出现的人物，在当前片段描述中保持连贯。
[
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
{past_summary}
]
'''


class RefrigeratorMonitorPrompt(BasePrompt):
	TASK_NAME: str = TASKNAME.REFRIGERATOR_MONITOR.value

	@staticmethod
	def _remove_user_prompt_line(lines):
		return [ln for ln in lines if not ln.strip().startswith('用户提问:')]

	@staticmethod
	def _remove_subtitles_section(lines):
		out = []
		skip = 0
		for i, ln in enumerate(lines):
			if skip:
				skip -= 1
				continue
			if ln.strip().startswith('##字幕:'):
				skip = 1
				if i + 2 < len(lines) and not lines[i + 2].strip():
					skip = 2
				continue
			out.append(ln)
		while out and not out[0].strip():
			out.pop(0)
		while out and not out[-1].strip():
			out.pop()
		return out

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

	rp = RefrigeratorMonitorPrompt()

	# Global prompt examples
	global_kwargs = {
		"question": "请统计冰箱门打开次数及涉及的人物",
	}
	global_kwargs_minimal = {}

	# Macro prompt examples
	macro_kwargs = {
		"question": "请汇总这一时间段内的冰箱使用情况",
		"st_tm": 0,
		"end_tm": 30,
	}

	# Local prompt examples
	local_kwargs = {
		"question": "请描述此片段中与冰箱的交互",
		"st_tm": 10,
		"end_tm": 20,
	}
	local_kwargs_minimal = {"st_tm": 10, "end_tm": 20}

	# T-minus prompt example
	tminus_kwargs = {
		"dur": 10,
		"st_tm": 0,
		"end_tm": 10,
		"past_summary": "一位穿白色T恤的人打开了冰箱门，从中取出一瓶矿泉水。",
	}

	print("=== GLOBAL (with question) ===\n")
	print(rp.assign_global_prompt(**global_kwargs))

	print("\n=== GLOBAL (minimal) ===\n")
	print(rp.assign_global_prompt(**global_kwargs_minimal))

	print("\n=== MACRO ===\n")
	print(rp.assign_macro_prompt(**macro_kwargs))

	print("\n=== LOCAL (with question) ===\n")
	print(rp.assign_local_prompt(**local_kwargs))

	print("\n=== LOCAL (minimal) ===\n")
	print(rp.assign_local_prompt(**local_kwargs_minimal))

	print("\n=== T-MINUS ===\n")
	print(rp.assign_t_minus_prompt(**tminus_kwargs))
