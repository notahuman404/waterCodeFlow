"""
Insights engine for CodeVovle.

Provides AI-powered code change analysis using multiple models.
Supports: Gemini (default), ChatGPT, Claude
Read-only; no mutations to state.
"""

import json
import os
from typing import Optional

from codevovle.engine import RecordingEngine
from codevovle.storage import StateManager, BranchManager, DiffManager, SnapshotManager
from codevovle.diffs import apply_patch_chain, compute_unified_diff
from codevovle.env_manager import EnvManager


class InsightsError(Exception):
    """Insights engine error."""
    pass


class InsightsEngine:
    """
    Generates AI-powered insights from code changes.
    
    Reconstructs code states at two points in time, computes diff,
    and sends to configured AI model for analysis.
    
    Supports multiple models:
    - Gemini (default)
    - ChatGPT
    - Claude
    """
    
    SUPPORTED_MODELS = ['gemini', 'chatgpt', 'claude']
    DEFAULT_MODEL = 'gemini'
    
    def __init__(self, file_path: str, model: Optional[str] = None):
        """
        Initialize insights engine.
        
        Args:
            file_path: File path to analyze
            model: AI model to use ('gemini', 'chatgpt', 'claude')
                   Defaults to 'gemini'
        """
        self.file_path = file_path
        self.model = model or self.DEFAULT_MODEL
        
        if self.model.lower() not in self.SUPPORTED_MODELS:
            raise InsightsError(f"Unsupported model: {self.model}")
        
        self.model = self.model.lower()

        # If model not explicitly provided, try to pick an available model.
        # Prefer the default model if an API key exists; otherwise pick the first
        # available model. If no keys are configured, defer error until
        # generate_insights is called.
        if model is None:
            available = EnvManager.get_available_models()
            if EnvManager.has_api_key(self.DEFAULT_MODEL):
                self.model = self.DEFAULT_MODEL
            elif available:
                # Pick first available model (e.g., 'claude' if CLAUDE_API_KEY set)
                self.model = available[0]
            else:
                # keep default; generate_insights will raise if no key
                self.model = self.DEFAULT_MODEL
    
    def _parse_tick_spec(self, spec: str, file_path: str) -> tuple[str, int]:
        """
        Parse tick specification.
        
        Format: "branch@tick" or "tick" (uses current branch)
        
        Args:
            spec: Tick specification
            file_path: File path for cursor reference
            
        Returns:
            Tuple of (branch, tick)
            
        Raises:
            InsightsError: If spec is invalid
        """
        if "@" in spec:
            parts = spec.split("@")
            if len(parts) != 2:
                raise InsightsError(f"Invalid tick spec: {spec}")
            branch, tick_str = parts
            try:
                tick = int(tick_str)
            except ValueError:
                raise InsightsError(f"Invalid tick number: {tick_str}")
            return branch, tick
        else:
            try:
                tick = int(spec)
            except ValueError:
                raise InsightsError(f"Invalid tick spec: {spec}")
            
            cursor = StateManager.get_cursor(file_path)
            if not cursor:
                raise InsightsError("No tracking initialized")
            
            return cursor["active_branch"], tick
    
    def _reconstruct_state(self, file_path: str, branch: str, tick: int) -> str:
        """
        Reconstruct code state at a specific tick.
        
        Args:
            file_path: File path
            branch: Branch name
            tick: Tick ID
            
        Returns:
            Reconstructed code state
            
        Raises:
            InsightsError: If reconstruction fails
        """
        try:
            branch_data = BranchManager.read(branch)
            if not branch_data or tick not in branch_data.get("diff_chain", []):
                raise InsightsError(f"Tick {tick} not found on branch {branch}")
            
            base = SnapshotManager.read()
            diff_chain = branch_data["diff_chain"]
            tick_index = diff_chain.index(tick)
            diffs_to_apply = diff_chain[:tick_index + 1]
            
            return apply_patch_chain(
                base,
                [DiffManager.read(t) for t in diffs_to_apply]
            )
        except Exception as e:
            raise InsightsError(f"Failed to reconstruct state: {e}") from e
    
    def generate_insights(self, from_spec: str, to_spec: str) -> dict:
        """
        Generate insights from code changes.
        
        Args:
            from_spec: Starting point ("branch@tick" or "tick")
            to_spec: Ending point ("branch@tick" or "tick")
            
        Returns:
            Structured insights response
            
        Raises:
            InsightsError: If generation fails or API key missing
        """
        from_branch, from_tick = self._parse_tick_spec(from_spec, self.file_path)
        to_branch, to_tick = self._parse_tick_spec(to_spec, self.file_path)
        
        old_state = self._reconstruct_state(self.file_path, from_branch, from_tick)
        new_state = self._reconstruct_state(self.file_path, to_branch, to_tick)
        
        diff = compute_unified_diff(old_state, new_state)
        
        payload = {
            "file_path": self.file_path,
            "from_tick": from_tick,
            "from_branch": from_branch,
            "to_tick": to_tick,
            "to_branch": to_branch,
            "diff": diff,
            "old_state": old_state,
            "new_state": new_state
        }
        
        # Get API key for selected model
        api_key = EnvManager.get_api_key(self.model)
        if not api_key:
            # Provide a helpful message including common env var names used in docs/tests
            raise InsightsError(
                f"API key not configured for {self.model}\n"
                "Set GEMINI_API_KEY, CHATGPT_API_KEY, or CLAUDE_API_KEY in environment or .env file"
            )
        
        try:
            if self.model == 'gemini':
                response = self._call_gemini(api_key, payload)
            elif self.model == 'chatgpt':
                response = self._call_chatgpt(api_key, payload)
            elif self.model == 'claude':
                response = self._call_claude(api_key, payload)
            else:
                raise InsightsError(f"Unknown model: {self.model}")
            
            return {
                "status": "success",
                "model": self.model,
                "insights": response,
                "file_path": self.file_path,
                "from": f"{from_branch}@{from_tick}",
                "to": f"{to_branch}@{to_tick}"
            }
        except Exception as e:
            raise InsightsError(f"{self.model.upper()} API call failed: {e}") from e
    
    def _call_gemini(self, api_key: str, payload: dict) -> dict:
        """
        Call Google Gemini API with code analysis request.
        
        Args:
            api_key: Gemini API key
            payload: Request payload
            
        Returns:
            API response
            
        Raises:
            InsightsError: If API call fails
        """
        import urllib.request
        import urllib.error
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        prompt = f"""Analyze the following code changes and provide insights:

FILE: {payload['file_path']}
FROM: {payload['from_branch']}@{payload['from_tick']}
TO: {payload['to_branch']}@{payload['to_tick']}

DIFF:
{payload['diff']}

OLD STATE:
{payload['old_state']}

NEW STATE:
{payload['new_state']}

Please provide a concise analysis of what changed and why it might matter."""
        
        request_data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        json_data = json.dumps(request_data).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Content-Type": "application/json"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                candidates = response_data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return {"analysis": content}
                return {"analysis": "No response from Gemini"}
        except urllib.error.HTTPError as e:
            raise InsightsError(f"API error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise InsightsError(f"Network error: {e.reason}") from e
    
    def _call_chatgpt(self, api_key: str, payload: dict) -> dict:
        """
        Call OpenAI ChatGPT API with code analysis request.
        
        Args:
            api_key: ChatGPT API key
            payload: Request payload
            
        Returns:
            API response
            
        Raises:
            InsightsError: If API call fails
        """
        import urllib.request
        import urllib.error
        
        url = "https://api.openai.com/v1/chat/completions"
        
        prompt = f"""Analyze the following code changes and provide insights:

FILE: {payload['file_path']}
FROM: {payload['from_branch']}@{payload['from_tick']}
TO: {payload['to_branch']}@{payload['to_tick']}

DIFF:
{payload['diff']}

OLD STATE:
{payload['old_state']}

NEW STATE:
{payload['new_state']}

Please provide a concise analysis of what changed and why it might matter."""
        
        request_data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1024
        }
        
        json_data = json.dumps(request_data).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                choices = response_data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return {"analysis": content}
                return {"analysis": "No response from ChatGPT"}
        except urllib.error.HTTPError as e:
            raise InsightsError(f"API error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise InsightsError(f"Network error: {e.reason}") from e
    
    def _call_claude(self, api_key: str, payload: dict) -> dict:
        """
        Call Anthropic Claude API with code analysis request.
        
        Args:
            api_key: Claude API key
            payload: Request payload
            
        Returns:
            API response
            
        Raises:
            InsightsError: If API call fails
        """
        import urllib.request
        import urllib.error
        
        url = "https://api.anthropic.com/v1/messages"
        
        prompt = f"""Analyze the following code changes and provide insights:

FILE: {payload['file_path']}
FROM: {payload['from_branch']}@{payload['from_tick']}
TO: {payload['to_branch']}@{payload['to_tick']}

DIFF:
{payload['diff']}

OLD STATE:
{payload['old_state']}

NEW STATE:
{payload['new_state']}

Please provide a concise analysis of what changed and why it might matter."""
        
        request_data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        json_data = json.dumps(request_data).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                content = response_data.get("content", [{}])[0].get("text", "")
                return {"analysis": content}
        except urllib.error.HTTPError as e:
            raise InsightsError(f"API error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise InsightsError(f"Network error: {e.reason}") from e
    
    @staticmethod
    def get_available_models() -> list[str]:
        """Get list of available AI models with configured API keys."""
        return EnvManager.get_available_models()
