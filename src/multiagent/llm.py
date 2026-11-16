from typing import Optional
import os
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_ollama import ChatOllama


class OllamaChatModel(ChatOllama):
    think: Optional[bool] = None

    def _chat_params(self, messages, stop=None, **kwargs):
        params = super()._chat_params(messages, stop=stop, **kwargs)
        if self.think is not None:
            params["think"] = self.think
        return params

    def with_structured_output(self, schema, *, method="json_schema", **kwargs):
        return super().with_structured_output(schema, method=method, **kwargs)


class LLM:
    def __init__(self, config):
        self.config = config
        self.loadLLM()

    def loadLLM(self):
        llm_sec = self.config["LLM"] if "LLM" in self.config else {}
        temperature = float(llm_sec.get("temperature", "0"))
        provider = llm_sec.get("provider", "ollama").strip().lower()
        num_predict = int(llm_sec.get("num_predict", "2048"))
        num_ctx = int(llm_sec.get("num_ctx", "8192"))

        if provider in ["vllm", "openai", "local_openai"]:
            base_url = llm_sec.get("base_url", "http://127.0.0.1:8000/v1")
            model = llm_sec.get("model", "Qwen/Qwen3-8B")
            api_key = self.config.get("KEYS", {}).get("OPENAI_API_KEY", "EMPTY")
            if not api_key or api_key.startswith("***"):
                api_key = "EMPTY"

            self.llm = ChatOpenAI(
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
                max_tokens=num_predict,
            )

        elif provider == "ollama":
            think_val = str(llm_sec.get("think", "false")).strip().lower()
            think = think_val in ["true", "1", "yes"]

            self.llm = OllamaChatModel(
                model=llm_sec.get("model", "qwen3:8b"),
                base_url=llm_sec.get("base_url", "http://localhost:11434"),
                temperature=temperature,
                num_predict=num_predict,
                num_ctx=num_ctx,
                think=think,
            )

        elif provider == "azure":
            self.openai_api_key = str(self.config["KEYS"]["OPENAI_API_KEY"])
            self.azure_endpoint = str(self.config["KEYS"]["OPENAI_ENDPOINT"])

            assert "************" not in self.openai_api_key, (
                "Error: Please input Azure API keys."
            )

            self.llm = AzureChatOpenAI(
                deployment_name=llm_sec["deployment_name"],
                openai_api_version=llm_sec["openai_api_version"],
                openai_api_key=self.openai_api_key,
                azure_endpoint=self.azure_endpoint,
                temperature=temperature,
            )

        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider!r}. "
                "Choose 'vllm', 'openai', 'ollama', or 'azure'."
            )
