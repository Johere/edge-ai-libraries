# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
Prompt templates for daily report generation from refrigerator monitoring events.
Focused on narrative daily summaries with statistics, anomaly detection, and health insights.
"""
from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME

# Global summary prompt for the entire day
## Optional: with user input question as customized
GLOBAL_PROMPT = '''
##任务:
你正在生成一份智能家居冰箱的每日使用报告。请根据以下全天的事件记录，生成一份结构化的日报。
用户提问: {question}

##报告要求:
- 生成一份叙事性的每日总结，按时间段组织内容（如：早晨、下午、晚上）
- 统计关键指标：
  * 冰箱门打开总次数
  * 总使用时长
  * 涉及的不同人物数量（通过衣着、体型等特征区分）
  * 高峰使用时段
- 识别异常行为：
  * 长时间未关闭冰箱门（>30秒）
  * 深夜时段开门（23:00-06:00）
  * 频繁开关门（短时间内多次）
- 物品进出情况：重点记录取出/放入的物品类型和数量
- 物资补充建议：根据取出物品的频率和类型，提供补充建议（如有）
- 饮食结构建议：根据取出食品的类型和时间分布，评估饮食健康性并提供建议（如有）
- 静态时段：概括长时间无活动的时段
- 输出应该是连贯的段落文字，不要使用时间戳或列表格式

##待总结内容:
以下是全天各时段的事件描述，每个事件用分隔符 ">|<" 分开。
'''

# Macro chunk prompt for summarizing a time period
## Optional: with user input question as customized
MACRO_CHUNK_PROMPT = '''
##任务:
你正在汇总某个时间段内的冰箱使用情况。请将该时段的事件串联起来，保持时间顺序。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##指南:
- 按时间顺序整理事件
- 合并同一人物的连续操作
- 记录物品进出情况
- 标记该时段内的异常行为（长时间开门、深夜开门、频繁开关）
- 区分有活动时段和静态时段
- 输出中不要包含具体时间戳，不要包含 "[" 或 "]"

##待总结内容:
以下是该时段各子事件的描述，每个子事件用分隔符 ">|<" 分开。
每个子事件的时间戳已在事件描述中体现。
- 输出中不要重复 "开始时间" 和 "结束时间"。
'''

# Local prompt for summarizing a single event
## Optional: with user input question as customized
LOCAL_PROMPT = '''
##任务:
请描述以下事件的详细内容。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##指南:
- 如果是静态时段（无活动），简要说明"冰箱门保持关闭，无活动"
- 如果是运动时段（有人打开冰箱），详细描述：
  * 人物特征（衣着、体型等）
  * 取出或放入的物品
  * 动作持续时间和特点
- 不要输出时间戳，不要包含 "[" 或 "]"
- 输出中不要包含 "开始时间" 和 "结束时间"

##事件内容:
{chunk_subtitle}
'''

# Previous context prompt for providing context from previous chunk
T_MINUS_1_PROMPT = '''
##上下文:
前 {dur} 秒的事件总结放在方括号 [] 中。
**重要** 需要将上一时段的描述视为上下文，并总结接下来的时段事件。
**重要** 不要在输出中复制上一时段的总结。
**重要** 注意上一时段中的人物和活动，在当前时段描述中保持连贯。
[
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
{past_summary}
]
'''


class DailyReportPrompt(BasePrompt):
	TASK_NAME: str = TASKNAME.DAILY_REPORT.value

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

	rp = DailyReportPrompt()

	# Global prompt examples
	global_kwargs = {
		"question": "请生成今日冰箱使用报告，包含统计数据和健康建议",
	}
	global_kwargs_minimal = {}

	# Macro prompt examples
	macro_kwargs = {
		"question": "请汇总这一时间段内的冰箱使用情况",
		"st_tm": 0,
		"end_tm": 3600,
	}

	# Local prompt examples
	local_kwargs = {
		"question": "",
		"st_tm": 10,
		"end_tm": 20,
		"chunk_subtitle": "一位穿白色T恤的人打开冰箱门，从上层取出一瓶牛奶。"
	}
	local_kwargs_minimal = {
		"st_tm": 10,
		"end_tm": 20,
		"chunk_subtitle": "冰箱门保持关闭，无活动"
	}

	# T-minus prompt example
	tminus_kwargs = {
		"dur": 600,
		"st_tm": 0,
		"end_tm": 600,
		"past_summary": "早晨8点左右，一位穿白色T恤的人打开了冰箱门两次，取出了牛奶和面包。",
	}

	print("=== GLOBAL (with question) ===\n")
	print(rp.assign_global_prompt(**global_kwargs))

	print("\n=== GLOBAL (minimal) ===\n")
	print(rp.assign_global_prompt(**global_kwargs_minimal))

	print("\n=== MACRO ===\n")
	print(rp.assign_macro_prompt(**macro_kwargs))

	print("\n=== LOCAL (with subtitle) ===\n")
	print(rp.assign_local_prompt(**local_kwargs))

	print("\n=== LOCAL (minimal/static) ===\n")
	print(rp.assign_local_prompt(**local_kwargs_minimal))

	print("\n=== T-MINUS ===\n")
	print(rp.assign_t_minus_prompt(**tminus_kwargs))
