# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
Prompt templates for Engine Valve Workstation SOP Checking on surveillance videos.
"""
import base64
from pathlib import Path
from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME

SYSTEM_PROMPT = '''
"你是一个专业的视频分析专家，擅长通过多模态上下文学习理解视频内容。请仔细学习用户提供的标注示例，然后理解视频中的关键实体并基于此分析视频。"
'''

# Visual entity reference templates
VISUAL_ENTITY_PROMPT = '''
[图片{index} - 带框标注]: data:image/jpeg;base64,{image_b64}
{description}
'''

# Local (vision-language) summary prompt for the entire video
# Optional: with user input question as customized
LOCAL_PROMPT = '''

### 角色设定
你是一个气门间隙检测工作站工业流程合规性检测专家。你的任务是接收一段视频, 首先生成详细的时间戳描述, 然后严格对照“标准步骤集”进行合规性判别。
用户要求: {question}

## 第一阶段: 标准步骤集 (SOP - 判别依据)
这是本次任务的“标准作业程序”。仅关注以下动作或相关动作, 并认为只有符合以下定义的动作才被视为“被执行(True)”。
每个工步会有详细描述, 包括: 工步内容, 动作简述, 动作起始标志, 动作结束标志, 工艺控制点。
注意有的工步不会出现(例如工步1、工步2), 有的工步会合并(例如工步4-6、工步10-13), 详细请见以下描述。
**重要： 实际操作过程中可能未按照工步顺序执行，在满足工步依赖的前提下是未按顺序执行工步是允许的。**
**工步3.** 
- 工步内容: 进气摇臂气门间隙检查确认工艺.将凸轮轴固定到相应检查角度时,晃动过桥, 保证其完全落入气门头部,用塞尺检查进气摇臂压头和过桥之间的间隙。
- 动作简述: 塞尺检查。
- 动作起始标志: 1. 发动机产品到位 2. 凸轮轴盘车工装在起始位置
- 动作结束标志: 塞尺检查共完成三次
- 工艺控制点: 塞尺与3个进气侧气门交叉并停留1秒, 塞尺检查共完成三次,三次位置对应三个进气侧气门间隙

**工步4-6.** 
- 工步内容: 如果**工步3**检查发现问题, 则调整螺母, 否则跳过
- 动作简述: 调整螺母
- 动作起始标志: 1. 工步3已完成 2. 人员使用扳手调整气门的螺母
- 动作结束标志: 进行至少一次塞尺检查
- 工艺控制点: 进行至少一次塞尺检查

**工步7.** 
- 工步内容: 锁紧螺柱手带到底, 使用定值扳手拧紧进气摇臂的锁紧螺母,使用白漆笔画线标记, 并在记录单上记录相应气门间隙数据。
- 动作简述: 画线标记
- 动作起始标志: 工步3已完成
- 动作结束标志: 白漆笔画线累积3次
- 工艺控制点: 白漆笔画线累积三次, 三次位置对应三个进气侧气门间隙

**工步8.** 
- 工步内容: 将凸轮轴固定到相应检查角度。对面操作工放置摇臂压头翘起工装到缸盖上, 翘起排气摇臂压头。
- 动作简述: 盘车, 凸轮轴固定
- 动作起始标志: 1. 工步3已完成 2. 凸轮轴盘车工装被扳动
- 动作结束标志: 凸轮轴盘车工装被扳倒指定位置
- 工艺控制点: 人手扳动凸轮轴盘车工装, 凸轮轴盘车工装位于发动机指定对准位置

**工步9.** 
- 工步内容: 排气摇臂气门间隙检查确认工艺. 用塞尺检查排气摇臂压头和气门顶部之间的间隙.
- 动作简述: 塞尺检查
- 动作起始标志: 工步8已完成
- 动作结束标志: 塞尺检查共完成三次
- 工艺控制点: 塞尺与3个排气侧气门交叉并停留1秒, 塞尺检查共完成三次,三次位置对应三个排气侧气门间隙

**工步10-13.** 
- 工步内容: 如果**工步9**检查发现问题, 则调整螺母, 否则跳过
- 动作简述: 调整螺母
- 动作起始标志: 1. 工步9已完成 2. 人员使用扳手调整气门的螺母
- 动作结束标志: 进行至少一次塞尺检查
- 工艺控制点: 进行至少一次塞尺检查

**工步14.** 
- 工步内容: 锁紧螺柱手带到底, 使用定值扳手拧紧排气摇臂的锁紧螺母,使用白漆笔画线标记, 并在记录单上记录相应气门间隙数据使用定值扳手对所有排气侧缸的锁紧螺母进行复紧。
- 动作简述: 画线标记
- 动作起始标志: 工步9已完成
- 动作结束标志: 白漆笔画线累积3次
- 工艺控制点: 1.结合工步3, 白漆笔画线累积6次 2. 三次位置对应三个排气侧气门间隙

**工步15.** 
- 工步内容: 确认所有的气门间隙合格,凸轮轴回到上止点后,可放行缸盖。
- 动作简述: 回位确认
- 动作起始标志: 凸轮轴盘车工装回位, 脱离
- 动作结束标志: 无
- 工艺控制点: 1. 凸轮轴盘车工装扳回初始位置 2. 凸轮轴正时插销插入凸轮轴正时插孔 3. 凸轮轴盘车工装从发动机脱离

**工步16.** 
- 工步内容: 待工位放行按钮灯闪烁后按下放行按钮,将托盘放至下一工位。
- 动作简述: 放行
- 动作起始标志: 无
- 动作结束标志: 发动机产品放行
- 工艺控制点: 发动机离开指定位置

## 第二阶段: 当前任务(Query)
**Guidelines**: 
请严格遵循以下步骤进行分析: 
1. **描述**: 先按照时间戳详细描述视频中的实际画面。“标准步骤集”中的工步描述仅作为判别依据，请参照实际视频内容进行分析，请勿在实际操作描述中将未发生的操作按照以下标准进行编造。
2. **判别**: 对照“标准步骤集”, 逐一判别每个工步是否被执行。
3. **输出格式**: 请务必包含“实际操作步骤描述“和”工步执行判别结论“两个部分, 判别结果必须是**True**或者**False**, 并给出理由。

**模型输出示例**: 
**1.实际操作描述(按照实际时间戳进行修改)**
- 00:00-00:03: xxx
- 00:03-00:06: xxx
- ...
**2.工步执行判别结论(请勿增删工步)**
- 工步3: xxx -> **True**(理由: xxx)
- 工步4-6: xxx -> **False**(理由: xxx)
- 工步7: xxx -> **True**(理由: xxx)
- 工步8: xxx -> **True**(理由: xxx)
- 工步9: xxx -> **True**(理由: xxx)
- 工步10-13: xxx -> **False**(理由: xxx)
- 工步14: xxx -> **True**(理由: xxx)
- 工步15: xxx -> **True**(理由: xxx)
- 工步16: xxx -> **True**(理由: xxx)

## 待分析视频内容:
待分析视频的起始时间: {st_tm} 秒
待分析视频的结束时间: {end_tm} 秒
'''


# Global (language) summary prompt for the entire video
# Optional: with user input question as customized
GLOBAL_PROMPT = '''TBD'''


class EngineValvesSoPPrompt(BasePrompt):
    TASK_NAME: str = TASKNAME.ENGINE_VALVES_SOP.value
    
    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        self.grounding_references = [
            {
                "image_path": str(base_dir / "MM_ICL/engine_valves_sop/1-img1_vis_entity_label.png"),
                "desc_path": str(base_dir / "MM_ICL/engine_valves_sop/1-img1_vis_entity_label_desc.txt"),
            },
            {
                "image_path": str(base_dir / "MM_ICL/engine_valves_sop/2-img2_vis_entity_label.png"),
                "desc_path": str(base_dir / "MM_ICL/engine_valves_sop/2-img2_vis_entity_label_desc.txt"),
            },
            {
                "image_path": str(base_dir / "MM_ICL/engine_valves_sop/3-img1_vis_label_engine.png"),
                "desc_path": str(base_dir / "MM_ICL/engine_valves_sop/3-img1_vis_label_engine_desc.txt"),
            },
            {
                "image_path": str(base_dir / "MM_ICL/engine_valves_sop/4-img1_vis_label_valve.png"),
                "desc_path": str(base_dir / "MM_ICL/engine_valves_sop/4-img1_vis_label_valve_desc.txt"),
            }
        ]

    @staticmethod
    def _remove_user_prompt_line(lines):
        return [ln for ln in lines if not ln.strip().startswith('用户要求:')]

    @staticmethod
    def _encode_image_to_base64(image_path: str) -> str:
        """Utility to encode an image file to base64 string."""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    
    def _generate_multimodal_prompt(self):
        # image format should be base64 encoded
        # Example format:
        # data:image/<format>;base64,<data>
        try:
            visual_entity = ""
            for index, grounding in enumerate(self.grounding_references, start=1):
                img_b64 = self._encode_image_to_base64(grounding["image_path"])
                with open(grounding["desc_path"], "r", encoding="utf-8") as f:
                    desc_text = f.read()
                cur_visual_entity = VISUAL_ENTITY_PROMPT.format(index=index, image_b64=img_b64, description=desc_text)
                visual_entity = visual_entity + cur_visual_entity + "\n"
            return visual_entity
        except Exception as e:
            raise RuntimeError(f"Error creating entity prompts: {e}")
        
    def assign_global_prompt(self, **kwargs) -> str:
        raise NotImplementedError("Global prompt not implemented for EngineValvesSoPPrompt")

    def assign_macro_prompt(self, **kwargs) -> str:
        raise NotImplementedError("Macro prompt not implemented for EngineValvesSoPPrompt")

    def assign_local_prompt(self, **kwargs) -> str:
        template = LOCAL_PROMPT
        q = kwargs.get('question', '')
        rendered = self._render_validated(
            template,
            kwargs,
            optional_fields={"question"}
        )
        lines = rendered.splitlines()
        if not str(q).strip():
            lines = self._remove_user_prompt_line(lines)
            
        return "\n".join(lines) + "\n"

    def assign_t_minus_prompt(self, **kwargs) -> str:
        raise NotImplementedError("T-minus prompt not implemented for EngineValvesSoPPrompt")


if __name__ == "__main__":
    from video_analyzer.utils.summarization_utils import redact_base64
    
    prompter = EngineValvesSoPPrompt()

	# Example inputs (replace with real paths/text in your integration)
    kwargs = {
        "task": "engine_valves_sop",
        "st_tm": 0,
        "end_tm": 39,
    }

    print("\n=== Prompt without question (line omitted) ===\n")
    print(redact_base64(prompter.assign_local_prompt(**kwargs)))