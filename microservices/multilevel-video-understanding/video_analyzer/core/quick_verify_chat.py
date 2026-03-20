"""
Quick verification script:
1) Read a video file
2) Sample frames with decord at 1 FPS, max 128, resize to 270x480
3) Generate SOP prompt (based on prompt_valve_sop) and call OpenAI Chat Completions API

Usage:
  python -m video_analyzer.core.quick_verify_chat --video /path/to/video.mp4

Environment:
  - Dependencies: decord, pillow, openai
"""

'''
Qwen/Qwen2.5-VL-7B-Instruct
Qwen/Qwen3-VL-32B-Thinking
Qwen/Qwen3-VL-32B-Instruct
Qwen/Qwen3-VL-30B-A3B-Thinking

B60: http://10.67.114.168:41091/v1
B60: http://10.67.111.27:41091/v1
A100: http://10.67.109.17:41091/v1

model_name="Qwen/Qwen3-VL-32B-Thinking"
api_key="Empty"
base_url="http://10.67.109.17:41091/v1"

model_name="Qwen/Qwen2.5-VL-32B-Instruct"
api_key="Empty"
base_url="http://10.67.111.27:41091/v1"

model_name = "google/gemini-3-pro-preview"
api_key = "1ea0622c64b049b999fd3f15552c78bc"
base_url = "https://api.xroute.ai/google/v1"

model_name = "gpt-5.2"
api_key = "1ea0622c64b049b999fd3f15552c78bc"
base_url = "https://api.xroute.ai/openai/v1"
'''

model_name="Qwen/Qwen3-VL-32B-Thinking"
api_key="Empty"
base_url="http://10.67.114.168:41091/v1"

# model_name = "gpt-5.2"
# api_key = "1ea0622c64b049b999fd3f15552c78bc"
# base_url = "https://api.xroute.ai/openai/v1"


import os
import base64
import argparse
import re
from typing import Any, Dict, List, Tuple, Optional
import requests

try:
    import decord
    from decord import VideoReader
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "decord is required. Install with: pip install decord"
    ) from e

from PIL import Image

from video_analyzer.core.prompt_valve_sop_refine_sop import (
    EngineValvesSoPPrompt,
)
from video_analyzer.model_serving.openai_vlm import VLM, LLM
from video_analyzer.core.settings import settings
from video_analyzer.utils.summarization_utils import redact_base64


def sample_video_frames(
    video_path: str,
    fps: int = 1,
    max_frames: int = 128,
    out_size: Tuple[int, int] = (270, 480),
) -> Tuple[List[Image.Image], List[float], float]:
    """Sample frames from a video using decord.

    - Samples approximately 1 frame per second
    - Caps frames at `max_frames`
    - Resizes each frame to (H=270, W=480)

    Returns: (frames, timestamps, duration_seconds)
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    vr = VideoReader(video_path, ctx=decord.cpu(0))
    total_frames = len(vr)
    avg_fps = float(vr.get_avg_fps()) if hasattr(vr, "get_avg_fps") else 30.0
    duration_sec = total_frames / avg_fps if avg_fps > 0 else 0.0

    # step: how many frames to skip to achieve ~1 FPS
    # Ensure step >= 1
    step = max(1, int(round(avg_fps / max(1, fps))))
    indices = list(range(0, total_frames, step))
    if len(indices) > max_frames:
        indices = indices[:max_frames]
    if not indices or indices[-1] != total_frames - 1:
        indices.append(total_frames - 1)

    # Batch read for efficiency
    batch = vr.get_batch(indices)  # (N, H, W, 3), uint8
    np_frames = batch.asnumpy()

    frames: List[Image.Image] = []
    timestamps: List[float] = []
    out_h, out_w = out_size
    for i, idx in enumerate(indices):
        arr = np_frames[i]
        img = Image.fromarray(arr)
        img = img.resize((out_w, out_h), resample=Image.BILINEAR)
        frames.append(img)
        timestamps.append(idx / avg_fps if avg_fps > 0 else 0.0)

    return frames, timestamps, duration_sec


def build_user_prompt_suffix(num_frames: int, timestamps: List[float]) -> str:
    """Build a succinct note about sampled frames to append to user question."""
    if num_frames == 0:
        return "(未抽取到任何帧)"
    # Show up to first 6 timestamps for brevity
    ts_preview = ", ".join(f"{t:.2f}s" for t in timestamps[:6])
    more = "..." if len(timestamps) > 6 else ""
    return f"(抽取帧数: {num_frames}, 示例时间戳: {ts_preview}{more})"

def call_vlm(frames: List[Image.Image], user_prompt: str, system_prompt: str=None) -> str:
    """Call OpenAI Chat Completions API and return the assistant message content."""
    
    # # debug
    # llm = LLM(
    #         model_name=model_name,
    #         api_key=api_key,
    #         base_url=base_url
    #     )
    
    # response = llm.infer(
    #     content="hi"
    # )
    
    vlm = VLM(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            individual_frames_in_prompt=True if "gpt" in model_name.lower() else False,
        )
    
    print(redact_base64(user_prompt))
    
    response = vlm.infer(
        frames=frames,
        content=user_prompt
    )
    
    if '</think>' in response:
        print(f"Model raw output (with thinking): {response}")
        response = vlm.remove_think_in_response(response)
    
    return response

def parse_multimodal_prompt_to_gemini(prompt: str) -> Tuple[List[Dict[str, Any]], bool]:
    """Split a unified prompt into Gemini-compatible parts list.

    Returns a tuple (parts, is_multimodal) where `parts` matches the expected
    `contents[0].parts` structure for Gemini requests: text chunks look like
    `{"text": "..."}` and media items look like
    `{"inline_data": {"mime_type": "image/jpeg", "data": "..."}}`.
    """

    if re.search(r"\b(?:file|https?)://", prompt, re.IGNORECASE):
        raise NotImplementedError(
            "Unsupported external references: file|http|https; only base64 data URLs are supported"
        )

    pattern = re.compile(
        r"(?P<url>data:(?P<mime>image/[\w.+-]+);base64,(?P<data>[A-Za-z0-9+/=]+))",
        re.IGNORECASE,
    )

    parts: List[Dict[str, Any]] = []
    is_multimodal = False
    pos = 0

    def _append_text(chunk: str):
        text = chunk.strip()
        if text:
            parts.append({"text": text})

    for match in pattern.finditer(prompt):
        before = prompt[pos:match.start()]
        _append_text(before)

        mime_type = match.group("mime").lower()
        data_b64 = match.group("data")
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": data_b64,
                }
            }
        )
        is_multimodal = True
        pos = match.end()

    _append_text(prompt[pos:])

    if not parts:
        parts.append({"text": prompt})

    if not is_multimodal:
        return ([{"text": prompt}], False)

    return parts, True

def encode_image_to_b64(image_path):
    with open(image_path, "rb") as image_file:
        # 读取二进制数据并进行 Base64 编码
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def call_gemini_chat(
    video_path: str, 
    user_prompt: str,
    system_prompt: Optional[str] = None,
) -> str:
    """Call Gemini 3 Pro-compatible API via raw HTTP request."""

    model_name="google/gemini-3-pro-preview"
    api_key="1ea0622c64b049b999fd3f15552c78bc"
    base_url="https://api.xroute.ai/google/v1/chat/completions"

    # Construct request messages for Qwen format
    if isinstance(user_prompt, str):
        '''
        (content, is_multimodal)
            - content: A list of content parts like
              [{"type":"text","text":"..."}, {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}, ...]
            - is_multimodal: True if any image/video tokens were found; False for pure text
        '''
        parts, is_multimodal = parse_multimodal_prompt_to_gemini(user_prompt)
    video_b64 = base64.b64encode(open(video_path, "rb").read()).decode("utf-8")
    parts.append(
        {
            "inline_data": {
                "mime_type": "video/mp4",
                "data": video_b64
            }
        }
    )
    
    '''
    An example for gemini multimodal content:
    
    "contents": [
        {
        "role": "user",
        "parts": [
            {
                "text": "请根据这张图片和这段视频，描述视频中是否出现了图片里的物体，并总结它们的关系。"
            },
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": "/9j/4AAQSkZJRgABAQAAAQABAAD...（此处为图像的Base64字符串）"
                }
            },
            {
                "inline_data": {
                    "mime_type": "video/mp4",
                    "data": "AAAAIGZ0eXBtcDQyAAAAAG1wND...（此处为视频的Base64字符串）"
                }
            }
        ]
        }
    ]
    '''
    contents = [{
                    "role": "user",
                    "parts": parts
               }]
    
    # # debug
    # image_b64 = encode_image_to_b64("/home/linjiaojiao/projects/large-model-quickstart/arcfact_sop_check/mm-prompts/1-img1_vis_entity_label.png")
    # contents = [{
    #                 "role": "user",
    #                 "parts": [
    #                     {"text": "hi"},
    #                     {
    #                         "inline_data": {
    #                             "mime_type": "image/jpeg",
    #                             "data": image_b64
    #                         }
    #                     }
    #                 ]
    #             }]

    '''
    curl --location 'https://api.xroute.ai/google/v1/chat/completions' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer 1ea0622c64b049b999fd3f15552c78bc' \
    -d '{
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "hi"
                    }
                ]
            }
        ],
        "model":"google/gemini-3-pro-preview",
        "generationConfig": {}
    }'

    '''
    payload = {
        "model": model_name,
        "contents": contents,
        "generationConfig": {},
    }

    print(redact_base64(payload))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    '''
    Debug log:
    usageMetadata":{"promptTokenCount":10921,"candidatesTokenCount":734,"totalTokenCount":17977,"promptTokensDetails":[{"modality":"IMAGE","tokenCount":4400},{"modality":"TEXT","tokenCount":2961},{"modality":"VIDEO","tokenCount":3560}],"thoughtsTokenCount":6322},"modelVersion":"gemini-3-pro-preview","responseId":"EqtDaYD5L9zVz7IP26D6kAI"}
    === Gemini 3 Pro Response ===

    ### 1. 实际操作描述
    - **00:00-00:08**: 操作人员手持塞尺，依次插入三个气门摇臂压头与过桥之间的缝隙进行间隙检查（对应进气侧气门位置）。
    - **00:09-00:14**: 操作人员放下塞尺，拿起白漆笔，依次在刚才检查过的三个气门螺母处进行画线标记。
    - **00:15-00:19**: 操作人员用手依次晃动三个气门的过桥（摇臂压头接触部位），检查其是否落入气门头部或是否有松动。
    - **00:20-00:27**: 操作人员拿起定值力矩扳手，依次对这三个气门的锁紧螺母进行拧紧操作。
    - **00:28-00:32**: 操作人员再次拿起白漆笔，在拧紧后的三个螺母处进行二次画线标记。
    - **00:33-00:39**: 操作人员再次拿起塞尺，对锁紧后的三个气门进行间隙复查，直至视频结束。

    ### 2. 工步执行判别结论
    - **工步3**: 进气摇臂气门间隙检查确认工艺 -> **True** (理由: 视频00:00-00:08及00:33-00:39期间，操作人员使用了塞尺对3个进气侧气门进行了间隙检查，且在00:15进行了晃动过桥的操作，符合工步核心动作要求)
    - **工步4-6**: 调整螺母 -> **False** (理由: 视频中未见操作人员使用普通扳手进行间隙调整动作，直接进行了拧紧，说明间隙合格无需调整，该工步被跳过)
    - **工步7**: 锁紧螺母并画线 -> **True** (理由: 视频00:20-00:27操作人员使用了定值扳手拧紧了3个气门的锁紧螺母，并在00:28-00:32完成了3次白漆笔画线标记，符合工步定义的动作和工艺控制点)
    - **工步8**: 盘车, 凸轮轴固定 -> **False** (理由: 视频全过程中，右侧的凸轮轴盘车工装保持静止，操作人员未执行盘车动作)
    - **工步9**: 排气摇臂气门间隙检查确认工艺 -> **False** (理由: 由于未执行工步8的盘车动作，且操作人员始终针对同一组气门进行操作，未切换至排气侧气门检查)
    - **工步10-13**: 调整螺母 -> **False** (理由: 前序工步未执行)
    - **工步14**: 锁紧螺母并画线 -> **False** (理由: 前序工步未执行)
    - **工步15**: 回位确认 -> **False** (理由: 视频结束时未见凸轮轴回位及插销操作)
    - **工步16**: 放行 -> **False** (理由: 发动机未离开工位)


    '''

    reply = requests.post(base_url, json=payload, headers=headers, timeout=settings.REQUEST_TIMEOUT)
    if reply.status_code != 200:
        raise RuntimeError(
            f"Gemini request failed ({reply.status_code}): {reply.text[:400]}"
        )
    print(f"request raw reply:{reply.text}")
    response = reply.json()['candidates'][0]['content']['parts'][0]['text']

    return response or "(Empty response)"


def main():
    parser = argparse.ArgumentParser(description="Quick SOP chat verification")
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--fps", type=int, default=1, help="Sampling FPS (default=1)")
    parser.add_argument("--max-frames", type=int, default=128, help="Max frames to sample")
    parser.add_argument(
        "--height", type=int, default=432, help="Resize height (default=432)"
    )
    parser.add_argument(
        "--width", type=int, default=768, help="Resize width (default=768)"
    )
    parser.add_argument(
        "--provider",
        choices=["vlm", "gemini"],
        default="vlm",
        help="Select inference backend",
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="User question appended to SOP prompt",
    )

    args = parser.parse_args()

    # 1) Sample frames
    frames, timestamps, duration = sample_video_frames(
        video_path=args.video,
        fps=args.fps,
        max_frames=args.max_frames,
        out_size=(args.height, args.width),
    )

    print(
        f"[decord] sampled {len(frames)} frames at ~{args.fps} FPS; duration ≈ {duration:.2f}s"
    )

    # 2) Build SOP local prompt
    prompter = EngineValvesSoPPrompt()
    user_prompt = prompter.assign_local_prompt(
        question=args.question,
        st_tm=0,
        end_tm=max(0, int(round(duration))),
    )

    # 3) Call selected backend
    try:
        if args.provider == "gemini":
            response = call_gemini_chat(
                args.video,
                user_prompt=user_prompt,
                system_prompt=None,
            )
            print("\n=== Gemini 3 Pro Response ===\n")
        else:
            response = call_vlm(frames, user_prompt, system_prompt=None)
            print("\n=== VLM Response ===\n")
        print(response)
    except Exception as e:
        print(f"[error] {args.provider} chat call failed: {e}")


if __name__ == "__main__":
    main()
