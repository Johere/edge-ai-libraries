# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
English prompt templates for refrigerator monitoring video summarization.
Tailored for smart home scenarios: door open/close detection, person identification,
item interaction tracking, and abnormal behavior alerting.
"""
from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME

# Global summary prompt for the entire video
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
GLOBAL_PROMPT_EN = '''
##Task:
You are analyzing a smart home refrigerator monitoring video. Based on all the following sub-clip descriptions, generate a coherent refrigerator usage event summary. Do not mention timestamps.
User prompt: {question}

##Guidelines:
- Output in narrative form; do not mention specific timestamps (seconds or minutes). The summary should read like a complete description.
- Count and report the following key metrics: number of times the refrigerator door was opened, approximate duration of each opening, and the number of different people involved.
- Focus on describing which items were taken out or put in during each door-opening event, including item types and characteristics.
- **Important** Flag abnormal behaviors: door left open for an extended period (over 30 seconds), rapid repeated opening and closing, frequent door openings during late-night hours, etc.
- **Important** Distinguish different people by appearance features such as clothing and body type; maintain consistent person references throughout.
- Do not fabricate content that does not appear in the video; strictly base the summary on the clip descriptions.

##Content to Summarize:
The following are summaries of each sub-section of the video.
Each sub-section is separated by the delimiter ">|<".
Each sub-section summary begins with its start and end times relative to the full video.
'''

# Macro chunk prompt for summarizing a group of micro chunks
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
MACRO_CHUNK_PROMPT_EN = '''
##Task:
You are analyzing a video clip from a smart home refrigerator monitoring camera. Please consolidate the following sub-clip descriptions, linking events along the timeline and preserving key timestamps.
User prompt: {question}

##Guidelines:
- Link events from each sub-clip in chronological order; merge consecutive actions by the same person.
- Highlight item changes: clearly record which items were taken out of and which were put back into the refrigerator.
- If the same person appears in multiple sub-clips, maintain consistent feature descriptions (e.g., "the person in a white T-shirt").
- Note that objects and scenes from earlier clips may not appear in the current clip; do not assume all clips contain the same elements.
- **Important** Preserve all details related to refrigerator interactions, including door opening/closing, item placement/removal, and person actions.
- Do not include "[" or "]" in the summary.

##Content to Summarize:
The following are summaries of each sub-section of the video clip.
Start time: {st_tm} seconds
End time: {end_tm} seconds
Each sub-section is separated by the delimiter ">|<".
Each sub-section summary begins with its start and end times relative to the full video.
- Do not repeat "Start time" or "End time" in the output.
'''

# Local prompt for summarizing a single micro chunk
## Optional: with user input question as customized
## Optional: with user provided subtitles (SubRip format) for the video
LOCAL_PROMPT_EN = '''
##Task:
You are analyzing a video clip from a smart home refrigerator monitoring camera. Please describe in detail all refrigerator-related activities in this clip.
Start time: {st_tm} seconds
End time: {end_tm} seconds
User prompt: {question}

##Guidelines:
- Focus on the following:
  1. Refrigerator door status: Whether the door is open, closed, or half-open; changes in door opening angle.
  2. Item interactions: Describe in detail each item taken out of or put into the refrigerator, including item type (food, beverage, container, etc.), color, shape, and packaging characteristics.
  3. Refrigerator interior: If the interior is visible, describe the visible arrangement of items.
  4. Person actions: Describe the specific actions of people in front of the refrigerator (bending, reaching, rummaging, standing and waiting, etc.).
- **Important** Keep the output concise while covering the key points above; this information will be used for subsequent event analysis and anomaly detection.
- If text appears in the frame (e.g., food labels), describe it in the original language and provide a translation in parentheses.
- If there is no refrigerator-related activity in this clip (e.g., a person merely walks past), describe the scene content as-is.
- Do not include "[" or "]" in the summary.
- Do not include "Start time" or "End time" in the output.
'''

# Previous context prompt for providing context from previous chunk
T_MINUS_1_PROMPT_EN = '''
##Context:
The summary of the previous {dur} seconds of video is placed in square brackets [].
**Important** Treat the previous clip's description as context and summarize the next video clip.
**Important** Do not copy the previous clip's summary into the output.
**Important** Pay attention to the refrigerator door status and people appearing in the previous clip; maintain continuity in the current clip description.
[
Start time: {st_tm} seconds
End time: {end_tm} seconds
{past_summary}
]
'''


class RefrigeratorMonitorEnPrompt(BasePrompt):
    TASK_NAME: str = TASKNAME.REFRIGERATOR_MONITOR_EN.value

    @staticmethod
    def _remove_user_prompt_line(lines):
        return [ln for ln in lines if not ln.strip().startswith('User prompt:')]

    @staticmethod
    def _remove_subtitles_section(lines):
        out = []
        skip = 0
        for i, ln in enumerate(lines):
            if skip:
                skip -= 1
                continue
            if ln.strip().startswith('##Subtitles:'):
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
        template = GLOBAL_PROMPT_EN
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
        template = MACRO_CHUNK_PROMPT_EN
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
        template = LOCAL_PROMPT_EN
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
            T_MINUS_1_PROMPT_EN,
            kwargs,
            optional_fields=set(),
        )


if __name__ == "__main__":
    from video_analyzer.utils.summarization_utils import redact_base64

    rp = RefrigeratorMonitorEnPrompt()

    # Global prompt examples
    global_kwargs = {
        "question": "Please count the number of refrigerator door openings and the people involved",
    }
    global_kwargs_minimal = {}

    # Macro prompt examples
    macro_kwargs = {
        "question": "Please summarize the refrigerator usage during this period",
        "st_tm": 0,
        "end_tm": 30,
    }

    # Local prompt examples
    local_kwargs = {
        "question": "Please describe the refrigerator interactions in this clip",
        "st_tm": 10,
        "end_tm": 20,
    }
    local_kwargs_minimal = {"st_tm": 10, "end_tm": 20}

    # T-minus prompt example
    tminus_kwargs = {
        "dur": 10,
        "st_tm": 0,
        "end_tm": 10,
        "past_summary": "A person in a white T-shirt opened the refrigerator door and took out a bottle of mineral water.",
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
