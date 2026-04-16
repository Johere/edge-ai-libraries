# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""
English prompt templates for daily report generation from refrigerator monitoring events.
Structured, concise output: statistics + inventory + insights.
"""
from video_analyzer.core.prompt_base import BasePrompt
from video_analyzer.schemas.summarization import TASKNAME

GLOBAL_PROMPT_EN = '''
##Task:
Summarize the following refrigerator events into a brief report.
**Important: The timestamps (HH:MM:SS) are real Beijing time in 24-hour format, NOT video playback time. Examples: 06:30 = 6:30 AM, 12:15 = 12:15 PM, 17:03 = 5:03 PM, 22:00 = 10:00 PM. Use these to accurately determine activity periods**
**Event types: Each SRT entry is prefixed with [motion] or [static]. [motion] = fridge door was opened — count these as door openings. [static] = idle period, no usage — do NOT count as door openings.**
User prompt: {question}

##Please strictly follow the template below (replace content in angle brackets; remove entire sections if no content applies):

Today's Refrigerator Activity Summary: <Two or three sentences summarizing main activities, including types of items involved and usage time patterns>

Current Inventory (estimated from today's activity):
- <Item A>: <quantity remaining> — <status: well-stocked / running low / used up>
- <Item B>: <quantity remaining> — <status>

Suggestions: <One sentence of advice>

User Habit Analysis: <One sentence describing peak times and frequency>

Dietary Advice: <One sentence of health advice>

##Example Output:

Today's Refrigerator Activity Summary: Mainly milk and yogurt were taken out, concentrated in the morning and evening periods, with higher frequency in the evening.

Inventory Alerts:
- Milk has only 1 carton remaining, suggest restocking
- Yogurt has been used up

User Habit Analysis: Door openings are concentrated between 7-8 AM and 6-7 PM; mornings are mainly for breakfast items.

##Rules:
- Do not list the time and details of each individual door opening
- Each section should be at most one sentence
- If there are no events, output only "No door opening events detected"

##Content to Summarize:
The following events are separated by ">|<".
'''

MACRO_CHUNK_PROMPT_EN = '''
##Task:
Summarize the refrigerator usage during this period in 2-3 sentences.
**Note: The timestamps in the events represent real wall-clock time (Beijing time) (e.g., 17:03 = 5:03 PM).**
**Event types: Each SRT entry is prefixed with [motion] or [static]. [motion] = fridge door was opened — count these as door openings. [static] = idle period, no usage — do NOT count as door openings.**
Start time: {st_tm} seconds
End time: {end_tm} seconds
User prompt: {question}

##Output Format (strictly 2-3 sentences):
Sentence 1: Items involved: <item name + quantity + taken out/put in>.
Sentence 2: <Change in remaining quantity>.
Sentence 3 (if applicable): <Abnormal behavior>.

##Example Output:
Items involved: 2 cartons of milk taken out, 1 bottle of soda put in. Milk has 1 carton remaining.

##Rules:
- Merge duplicate items, only write aggregated quantities
- Do not list each individual door opening
- Do not output "[" or "]"

##Content to Summarize:
The following sub-events are separated by ">|<".
'''

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

T_MINUS_1_PROMPT_EN = '''
##Previous Summary (do not copy, use as reference only):
{past_summary}
Start time: {st_tm} seconds
End time: {end_tm} seconds
'''


class DailyReportEnPrompt(BasePrompt):
    TASK_NAME: str = TASKNAME.DAILY_REPORT_EN.value

    @staticmethod
    def _remove_user_prompt_line(lines):
        return [ln for ln in lines if not ln.strip().startswith('User prompt:')]

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

    rp = DailyReportEnPrompt()

    # Global prompt examples
    global_kwargs = {
        "question": "Please generate today's refrigerator usage report with statistics and health advice",
    }
    global_kwargs_minimal = {}

    # Macro prompt examples
    macro_kwargs = {
        "question": "Please summarize the refrigerator usage during this period",
        "st_tm": 0,
        "end_tm": 3600,
    }

    # Local prompt examples
    local_kwargs = {
        "question": "",
        "st_tm": 10,
        "end_tm": 20,
        "chunk_subtitle": "A person in a white T-shirt opens the refrigerator door and takes out a carton of milk from the top shelf."
    }
    local_kwargs_minimal = {
        "st_tm": 10,
        "end_tm": 20,
        "chunk_subtitle": "Refrigerator door remains closed, no activity"
    }

    # T-minus prompt example
    tminus_kwargs = {
        "dur": 600,
        "st_tm": 0,
        "end_tm": 600,
        "past_summary": "Around 8 AM, a person in a white T-shirt opened the refrigerator door twice and took out milk and bread.",
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
