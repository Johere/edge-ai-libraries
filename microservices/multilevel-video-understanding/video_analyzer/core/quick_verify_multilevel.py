"""
Quick verification script:
1) Read a video file
2) Sample frames with decord at 1 FPS, max 128, resize to 270x480
3) Generate SOP prompt (based on prompt_valve_sop) and call OpenAI Chat Completions API

Usage:
  python -m video_analyzer.core.quick_verify_multilevel --video /path/to/video.mp4

Environment:
  - Dependencies: decord, pillow, openai
"""
import argparse

from video_analyzer.core.prompt_valve_sop import (
    EngineValvesSoPPrompt
)
from video_analyzer.core.settings import settings
from video_analyzer.utils.summarization_utils import remove_brackets
from quick_verify_chat import sample_video_frames, call_gemini_chat

def main():
    parser = argparse.ArgumentParser(description="Quick SOP chat verification based on multi-level video understanding")
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
        choices=["gemini"],
        default="gemini",
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
    _, _, duration = sample_video_frames(
        video_path=args.video,
        fps=args.fps,
        max_frames=args.max_frames,
        out_size=(args.height, args.width),
    )

    # 2) Build SOP local prompt
    prompter = EngineValvesSoPPrompt()

    # 3) Call selected backend
    try:
        if args.provider == "gemini":
            # level-0: vlm
            user_prompt = prompter.assign_local_prompt(
                question=args.question,
                st_tm=0,
                end_tm=max(0, int(round(duration))),
            )
            import pdb; pdb.set_trace()
            response = call_gemini_chat(
                args.video,
                user_prompt=user_prompt,
                system_prompt=None,
            )
            print("\n=== Gemini 3 Pro Level-0 Response ===\n")
            desc = remove_brackets(response)
            print(desc)
            # level-1: llm
            full_summ_prompt = prompter.assign_global_prompt(
                question=args.question,
            )
            full_summ_prompt += '\n\n>|<\n{}\n>|<'
            global_user_prompt = full_summ_prompt.format("\n>|<\n".join([desc]))
            import pdb; pdb.set_trace()
            final_summary = call_gemini_chat(
                args.video,
                user_prompt=global_user_prompt,
                system_prompt=None,
            )
            print("\n=== Gemini 3 Pro Level-1 Response ===\n")
            print(final_summary)
    except Exception as e:
        print(f"[error] {args.provider} chat call failed: {e}")


if __name__ == "__main__":
    main()
