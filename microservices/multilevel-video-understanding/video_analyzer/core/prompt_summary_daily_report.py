# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
Prompt templates for daily report generation from refrigerator monitoring events.
Structured, concise output: statistics + inventory + insights.
"""
from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME

GLOBAL_PROMPT = '''
##任务:
将以下冰箱事件汇总为简短报告。
**重要：以下 SRT 中的时间戳（HH:MM:SS）是北京时间真实钟表时间，不是视频播放时间。例如 17:03 表示下午5:03，07:30 表示早上7:30。请据此判断用户的活动时段（如早晨/中午/下午/傍晚/深夜）。**
用户提问: {question}

##请严格按以下模板输出（替换尖括号内容，无内容的板块整块删除）:

今日冰箱活动概括：<两三句话概括主要活动，包括涉及的物品种类和使用时段特征>

库存提醒：
- <物品A> 剩余不足，建议补充
- <物品B> 已取完

建议：<一句话建议>

用户习惯分析：<一句话，说明高峰时段和频率>

饮食建议：<一句话健康建议>

##示例输出:

今日冰箱活动概括：主要取用了牛奶和酸奶，集中在早晨和傍晚两个时段，傍晚取用频率较高。

库存提醒：
- 牛奶 剩余1盒，建议补充
- 酸奶 已取完

用户习惯分析：开门集中在早晨7-8点和傍晚18-19点，早晨以取早餐食品为主。

##规则:
- 禁止列出每次开门的时间和详情
- 每个板块最多一句话
- 无事件则只输出"未检测到开门事件"

##待总结内容:
以下事件用 ">|<" 分开。
'''

MACRO_CHUNK_PROMPT = '''
##任务:
用2-3句话汇总该时段冰箱使用情况。
**注意：事件中的时间戳是北京时间真实钟表时间（如 17:03 = 下午5:03）。**
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##输出格式（严格2-3句话）:
第1句：涉及物品：<物品名+数量+取出/放入>。
第2句：<剩余量变化>。
第3句（如有）：<异常行为>。

##示例输出:
涉及物品：牛奶取出2盒、可乐放入1瓶。牛奶剩余1盒。

##规则:
- 合并重复物品，只写汇总数量
- 禁止逐条列出每次开门
- 不输出"[" "]"

##待总结内容:
以下子事件用 ">|<" 分开。
'''

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

T_MINUS_1_PROMPT = '''
##前文摘要（不要复制，仅作参考）:
{past_summary}
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
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
