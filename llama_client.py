import os
from typing import List, Dict, Any, Optional, Union

import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
from config import config
from prompt_registry import build_tool_system_prompt


class LlamaClient:
    """Client for interacting with Gemini models via the Google Generative AI API."""

    def __init__(self, model_name: Optional[str] = None):
        self.config = config
        self.model_name = model_name or self.config.get('model.name', 'gemini-1.5-pro-latest')
        self.system_prompt_variant = self.config.get('prompts.system_prompt_variant', 'tool_use_reasoned')

        api_key_env = self.config.get('model.api_key_env', 'GOOGLE_API_KEY')
        api_key = os.getenv(api_key_env)

        if not api_key:
            raise EnvironmentError(
                f"Missing Gemini API key. Set the '{api_key_env}' environment variable."
            )

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model_name)
        print(f"✅ Using Gemini model: {self.model_name}")

    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]],
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            prior_tool_results: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Generate response with tool calling capability.

        Parameters
        ----------
        prior_tool_results : list[dict] | None
            Results from earlier iterations of the multi-tool loop.
            Each dict has ``tool_name`` and ``formatted_result`` keys.
            Passed through to ``build_tool_system_prompt`` so the LLM
            knows what data it already has.
        """
        temperature = temperature or self.config.get('model.temperature', 0.7)
        max_tokens = max_tokens or self.config.get('model.max_tokens', 2048)

        system_prompt = build_tool_system_prompt(
            self.system_prompt_variant,
            tools,
            prior_tool_results=prior_tool_results,
        )
        composed_prompt = f"{system_prompt}\n\nUser question: {prompt}"

        try:
            # Use simple approach without generation config for now
            response = self.client.generate_content(composed_prompt)

            # Handle potential safety filters or empty responses
            if hasattr(response, 'text') and response.text:
                return {
                    "content": response.text,
                    "needs_tool_call": "TOOL_CALL:" in response.text
                }
            else:
                return {
                    "content": "❌ No response generated (may have been filtered)",
                    "needs_tool_call": False
                }

        except Exception as e:
            return {"content": f"❌ Error generating response: {e}", "needs_tool_call": False}

    def generate(self, prompt: str,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None,
                 stream: bool = False) -> Union[str, Any]:
        """Generate a response from the model."""
        temperature = temperature or self.config.get('model.temperature', 0.7)
        max_tokens = max_tokens or self.config.get('model.max_tokens', 2048)

        try:
            if stream:
                response = self.client.generate_content(
                    prompt,
                    stream=True
                )
                return response

            response = self.client.generate_content(prompt)
            return getattr(response, 'text', str(response))

        except Exception as e:
            return f"❌ Error generating response: {e}"

    def generate_with_context(self, prompt: str, context: str,
                              temperature: Optional[float] = None,
                              max_tokens: Optional[int] = None) -> str:
        """Generate a response with provided context."""
        context_prompt = f"""Context: {context}

Question: {prompt}

Answer based on the context provided:"""

        return self.generate(context_prompt, temperature, max_tokens)
