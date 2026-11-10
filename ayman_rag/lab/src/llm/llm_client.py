"""Stage 4 — send the prompt to a language model and get the answer back.

Two options, chosen in config.yaml:
- "anthropic": Claude API. Needs ANTHROPIC_API_KEY in .env.  pip install anthropic
- "ollama":    a free model on your own machine. Install Ollama, then `ollama pull qwen2.5:7b`.
"""

import json
import os
import urllib.request


class LLMClient:
    def __init__(self, config: dict):
        self.cfg = config["llm"]

    def complete(self, system: str, user: str) -> str:
        if self.cfg["provider"] == "anthropic":
            return self._anthropic(system, user)
        if self.cfg["provider"] == "ollama":
            return self._ollama(system, user)
        raise ValueError(f"Unknown llm.provider: {self.cfg['provider']}")

    def _anthropic(self, system: str, user: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model=self.cfg["model"],
            max_tokens=self.cfg["max_tokens"],
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")

    def _ollama(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": self.cfg["ollama_model"],
            "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        req = urllib.request.Request("http://localhost:11434/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["message"]["content"]
