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
你正在分析一段家庭摄像头视频，目的是检测是否出现**儿童危险行为**。请基于以下所有子片段描述，生成一份以安全为导向的整体摘要。
用户提问: {question}

##重点关注的危险场景（critical/warn）:
- **critical**: 儿童手持刀具/剪刀、玩打火机或明火、攀爬窗户或阳台护栏、攀爬冰箱/柜子顶部、剧烈摔倒后长时间未起身。
- **warn**: 在沙发/床/桌面上蹦跳、追逐中撞到家具、独自爬上高凳、疑似吞食小件物品、用绳索/带子缠绕颈部。
- **info / normal_play**: 安全范围内的游戏、看书、看电视、与成人互动等。

##指南:
- 以叙事体输出，不要提及具体时间戳（秒或分钟），让摘要读起来像一段完整的描述。
- 按严重程度汇总：先陈述整体安全判断（"整体安全" / "出现 1 次 warn 级别行为" / "出现 critical 级别危险行为"），再展开事件细节。
- **重要** 如果任一子片段标注了 critical 行为，必须在摘要开头以"【注意】"开始并明确指出该行为。
- 描述儿童的外观特征（衣着、发型、大致身高/年龄段）以便跨片段一致指代；若有成人在场，简要说明成人是否在场监护。
- 统计并报告：出现的儿童人数、涉及的危险类型列表（如"刀具"、"打火机"、"攀爬窗户"）、成人介入次数。
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
你正在分析一段家庭摄像头视频片段。请汇总以下子片段描述，按时间顺序串联事件，**优先突出危险行为**。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##指南:
- 按时间顺序串联各子片段，合并同一儿童的连续动作。
- **重要** 如果任一子片段出现 critical 或 warn 行为，保留该行为的完整描述并在段首突出。
- 对于连续多个"normal_play"或"无人"片段，可合并为一句话（例如"该时段儿童在沙发区安全游戏"）。
- 保持儿童的外观特征描述一致（如"穿红色连衣裙的小女孩"）；若多名儿童出现，分别指代。
- 注意前面片段出现的人物/物品未必出现在当前片段，不要想当然。
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
你正在分析一段家庭摄像头短片段，目的是识别儿童是否处于**危险行为**。请详细描述该片段中与儿童安全相关的所有活动。
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
用户提问: {question}

##重点关注的内容:
1. **儿童出现与外观**：是否有儿童在画面中；若有，其衣着、大致身高/年龄段、所在位置（客厅/厨房/卧室/阳台/窗边/家具上）。
2. **危险物品接触**：儿童手中或身旁是否出现刀、剪刀、打火机、火源、药瓶、小件易吞物、绳索/塑料袋等。如出现，必须明确说明物品类型并估计接触方式（握持、把玩、含入口中等）。
3. **危险动作**：
   - 攀爬：窗台、阳台栏杆、冰箱、衣柜、书架、椅子叠高等。
   - 高处跳跃：沙发→地面、床→地面、桌面→沙发等。
   - 摔倒：是否发生摔倒、摔倒后是否自主起身、是否哭泣。
   - 其他：疑似吞食、拉扯电线、触碰插座、打开窗户等。
4. **成人监护**：画面中是否有成人在场、成人是否注意到儿童、是否进行干预。
5. **安全动作**（若没有危险）：正常游戏、看书、看电视、与成人互动等，简短描述即可。

##指南:
- **重要** 输出尽量简洁，优先包含上述 1–4 点，安全片段用 1–2 句描述即可。
- 对每个识别出的危险，给出严重度判断词："critical"（刀、火、攀爬窗/阳台、严重摔倒）、"warn"（家具蹦跳、轻微摔倒、爬高凳）、"info / normal_play"（安全场景）。
- 如果画面中出现文字（如药瓶标签），请以原语言描述并在括号中提供翻译。
- 如果该片段中没有儿童（如仅有成人路过或画面静止），也请如实描述画面内容。
- 摘要中不要包含 "[" 或 "]"。
- 输出中不要包含 "开始时间" 和 "结束时间"。
'''


# Previous context prompt for providing context from previous chunk
T_MINUS_1_PROMPT = '''
##上下文:
前 {dur} 秒的视频总结放在方括号 [] 中。
**重要** 需要将上一片段的描述视为上下文，并总结接下来的视频片段。
**重要** 不要在输出中复制上一片段的总结。
**重要** 注意上一片段中儿童的位置、动作状态和是否接触危险物品，在当前片段描述中保持连贯；如果上一片段出现 critical/warn 行为但本片段已结束该行为，请明确说明（例如"儿童已放下刀具，成人接管"）。
[
开始时间: {st_tm} 秒
结束时间: {end_tm} 秒
{past_summary}
]
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
