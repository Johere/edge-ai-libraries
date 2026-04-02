# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI, AsyncOpenAI
import httpx

from video_analyzer.core.settings import settings
from video_analyzer.utils.logger import logger
from video_analyzer.utils.performance import ProfileTimer


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)."""
    return len(text) // 4


def _extract_api_metadata(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract metadata from messages for profiling and logging."""
    metadata = {
        "frame_count": 0,
        "estimated_input_tokens": 0,
        "is_vlm_call": False,
    }

    for msg in messages:
        content = msg.get("content", "")

        # Handle list of content parts (multimodal)
        if isinstance(content, list):
            for part in content:
                part_type = part.get("type", "")

                # Count frames for VLM calls
                if part_type == "video_url":
                    # video_url format: data:video/jpeg;base64,frame1,frame2,...
                    url = part.get("video_url", {}).get("url", "")
                    if url.startswith("data:video/jpeg;base64,"):
                        # Count frames by counting commas in base64 data
                        base64_data = url.split("base64,", 1)[1] if "base64," in url else ""
                        metadata["frame_count"] = base64_data.count(",") + 1 if base64_data else 0
                        metadata["is_vlm_call"] = True

                elif part_type == "image_url":
                    # Individual image format
                    metadata["frame_count"] += 1
                    metadata["is_vlm_call"] = True

                elif part_type == "text":
                    # Count text tokens
                    text_content = part.get("text", "")
                    metadata["estimated_input_tokens"] += _estimate_tokens(text_content)

        # Handle plain string content
        elif isinstance(content, str):
            metadata["estimated_input_tokens"] += _estimate_tokens(content)

    return metadata


class LLM:
    """
    Language model for text processing with concurrent processing support.
    
    This class provides an interface to interact with OpenAI API-compatible
    language models, supporting concurrent requests and configurable parameters.
    
    Args:
        model_name: Name of the language model to use
        api_key: API key for authentication (optional if set in environment)
        base_url: Base URL for the API endpoint (optional for OpenAI-compatible APIs)
        remove_thinking: Whether to remove thinking patterns from responses (optional)
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        remove_thinking: Optional[bool] = False,
    ):
        self.model_name = model_name

        # Use default values from config if parameters are None
        self.api_key = api_key
        self.base_url = base_url
        self.remove_thinking = remove_thinking
        logger.debug(f"Remove thinking: {'Enabled' if self.remove_thinking else 'Disabled'}")

        # Concurrency settings
        self.timeout = settings.MODEL_REQUEST_TIMEOUT
        self.max_retries = settings.MODEL_MAX_RETRIES
        self.temperature = settings.DEFAULT_TEMPERATURE

        # Create httpx client without proxy for local vllm connections
        # This ensures localhost/127.0.0.1 connections bypass proxy even in async context
        # Use longer timeout (10 minutes) for httpx transport to handle slow VLM inference
        # OpenAI SDK timeout (self.timeout) handles overall request timeout
        http_timeout = httpx.Timeout(timeout=600.0, connect=60.0)
        http_client = httpx.Client(proxy=None, timeout=http_timeout)
        async_http_client = httpx.AsyncClient(proxy=None, timeout=http_timeout)

        # Use remote inference
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, http_client=http_client)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, http_client=async_http_client)
        
        logger.debug(f"Using remote inference serving with model: {model_name} from endpoint: {self.base_url}")
    
    def infer(self, content: str|List[Dict[str, Any]]) -> str:
        """
        Run inference on a text prompt, in sync mode

        Args:
            content: 
                Option1. Text prompt to process
                Option2. List of contents with user's prompts to process

        Returns:
            Model's response
        """
        
        # Construct messages for the API
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": content}
        ]
        print(msgs)
        
        response = self._remote_infer(msgs)
        
        if self.remove_thinking:
            response = self.remove_think_in_response(response)
            
        return response
    
    async def async_infer(self, content: str|List[Dict[str, Any]]) -> str:
        """
        Run inference on a text prompt, in async mode

        Args:
            content: 
                Option1. Text prompt to process
                Option2. List of contents with user's prompts to process

        Returns:
            Model's response
        """
        
        # Construct messages for the API
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": content}
        ]
        
        response = await self._async_remote_infer(msgs)
        
        if self.remove_thinking:
            response = self.remove_think_in_response(response)
            
        return response
    
    def _remote_infer(self, messages: List[Dict[str, Any]]) -> str:
        """
        Run remote inference using OpenAI API.

        Args:
            messages: messages with user's prompts to process

        Returns:
            Model's response
        """
        retry_count = 0

        # Extract metadata for profiling
        api_metadata = _extract_api_metadata(messages)
        call_type = "VLM" if api_metadata["is_vlm_call"] else "LLM"

        while retry_count < self.max_retries:
            # Log API call details before request
            if api_metadata["is_vlm_call"]:
                logger.info(f"[API_CALL] {call_type} request: frames={api_metadata['frame_count']}, "
                           f"prompt_tokens~{api_metadata['estimated_input_tokens']}, timeout={self.timeout}s, "
                           f"attempt={retry_count+1}/{self.max_retries}")
            else:
                logger.info(f"[API_CALL] {call_type} request: input_tokens~{api_metadata['estimated_input_tokens']}, "
                           f"timeout={self.timeout}s, attempt={retry_count+1}/{self.max_retries}")

            start_time = time.monotonic()

            try:
                logger.debug(f"Sending request to remote LLM: {self.model_name} (attempt {retry_count+1}/{self.max_retries})")
                logger.debug(f"API base URL: {self.base_url}")

                # Profile and call the API
                profile_metadata = {
                    "model": self.model_name,
                    "call_type": call_type,
                    "frame_count": api_metadata["frame_count"],
                    "estimated_input_tokens": api_metadata["estimated_input_tokens"],
                    "attempt": retry_count + 1,
                }

                with ProfileTimer(f"{call_type.lower()}_api_call", profile_metadata):
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=self.temperature,
                        timeout=self.timeout,
                        max_tokens=512,
                        extra_body={
                            "chat_template_kwargs": {
                                "enable_thinking": False
                            }
                        },
                    )

                latency = time.monotonic() - start_time
                logger.debug(f"API call successful, response:{response}")

                content = response.choices[0].message.content.strip()

                # Log successful response with detailed metrics
                completion_tokens = response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else 0
                total_tokens = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0

                logger.info(f"[API_CALL] {call_type} response: latency={latency:.2f}s, "
                           f"completion_tokens={completion_tokens}, total_tokens={total_tokens}, status=success")
                logger.debug(f"Successfully received response from remote LLM")

                return content

            except Exception as e:
                latency = time.monotonic() - start_time
                logger.error(f"[API_CALL] {call_type} failed: latency={latency:.2f}s, error={str(e)}, "
                            f"attempt={retry_count+1}/{self.max_retries}")
                logger.error(f"ERROR in API call(URL: {self.base_url}) (attempt {retry_count+1}): {str(e)}")

                retry_count += 1
                if retry_count >= self.max_retries:
                    error_msg = f"Error: API call(URL: {self.base_url}) failed after {self.max_retries} attempts. Last error: {str(e)}"
                    logger.error(error_msg)
                    return error_msg
                
    async def _async_remote_infer(self, messages: List[Dict[str, Any]]) -> str:
        """
        Run remote inference asynchronously using OpenAI API.

        Args:
            messages: messages with user's prompts to process

        Returns:
            Model's response
        """
        retry_count = 0

        # Extract metadata for profiling
        api_metadata = _extract_api_metadata(messages)
        call_type = "VLM" if api_metadata["is_vlm_call"] else "LLM"

        while retry_count < self.max_retries:
            # Log API call details before request
            if api_metadata["is_vlm_call"]:
                logger.info(f"[API_CALL] {call_type} request: frames={api_metadata['frame_count']}, "
                           f"prompt_tokens~{api_metadata['estimated_input_tokens']}, timeout={self.timeout}s, "
                           f"attempt={retry_count+1}/{self.max_retries}")
            else:
                logger.info(f"[API_CALL] {call_type} request: input_tokens~{api_metadata['estimated_input_tokens']}, "
                           f"timeout={self.timeout}s, attempt={retry_count+1}/{self.max_retries}")

            start_time = time.monotonic()

            try:
                logger.debug(f"Sending async request to remote LLM: {self.model_name} (attempt {retry_count+1}/{self.max_retries})")

                # Profile and call the API
                profile_metadata = {
                    "model": self.model_name,
                    "call_type": call_type,
                    "frame_count": api_metadata["frame_count"],
                    "estimated_input_tokens": api_metadata["estimated_input_tokens"],
                    "attempt": retry_count + 1,
                }

                with ProfileTimer(f"{call_type.lower()}_api_call", profile_metadata):
                    response = await self.async_client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=self.temperature,
                        timeout=self.timeout,
                        max_tokens=512,
                        extra_body={
                            "chat_template_kwargs": {
                                "enable_thinking": False
                            }
                        },
                    )

                latency = time.monotonic() - start_time
                logger.debug(f"API call successful, response:{response}")

                content = response.choices[0].message.content.strip()

                # Log successful response with detailed metrics
                completion_tokens = response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else 0
                total_tokens = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0

                logger.info(f"[API_CALL] {call_type} response: latency={latency:.2f}s, "
                           f"completion_tokens={completion_tokens}, total_tokens={total_tokens}, status=success")
                logger.debug(f"Successfully received async response from remote LLM")

                return content

            except Exception as e:
                latency = time.monotonic() - start_time
                logger.error(f"[API_CALL] {call_type} failed: latency={latency:.2f}s, error={str(e)}, "
                            f"attempt={retry_count+1}/{self.max_retries}")
                logger.error(f"ERROR in async API call (attempt {retry_count+1}): {str(e)}")

                retry_count += 1
                if retry_count >= self.max_retries:
                    error_msg = f"Error: API call failed after {self.max_retries} attempts. Last error: {str(e)}"
                    logger.error(error_msg)
                    return error_msg
                # Wait before retrying
                await asyncio.sleep(1)

    @staticmethod
    def remove_think_in_response(response: str) -> str:
        index = response.rfind("</think>")
        if index > 0:
            response = response[index:]
            response = response.replace("</think>\n\n", "").replace("</think>", "")
        return response