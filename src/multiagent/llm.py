from typing import Optional
from langchain_openai import AzureChatOpenAI
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
        temperature = float(self.config["LLM"].get("temperature", "0"))
        provider = self.config["LLM"].get("provider", "azure").strip().lower()

        if provider == "ollama":
            num_predict = int(self.config["LLM"].get("num_predict", "2048"))
            num_ctx = int(self.config["LLM"].get("num_ctx", "8192"))
            think_val = str(self.config["LLM"].get("think", "false")).strip().lower()
            think = think_val in ["true", "1", "yes"]

            self.llm = OllamaChatModel(
                model=self.config["LLM"].get("model", "qwen3:8b"),
                base_url=self.config["LLM"].get(
                    "base_url", "http://localhost:11434"
                ),
                temperature=temperature,
                num_predict=num_predict,
                num_ctx=num_ctx,
                think=think,
            )

        elif provider == "azure":
            self.openai_api_key = str(
                self.config["KEYS"]["OPENAI_API_KEY"]
            )
            self.azure_endpoint = str(
                self.config["KEYS"]["OPENAI_ENDPOINT"]
            )

            assert "************" not in self.openai_api_key, (
                "Error: Please input Azure API keys."
            )

            self.llm = AzureChatOpenAI(
                deployment_name=self.config["LLM"]["deployment_name"],
                openai_api_version=self.config["LLM"]["openai_api_version"],
                openai_api_key=self.openai_api_key,
                azure_endpoint=self.azure_endpoint,
                temperature=temperature,
            )

        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider!r}. "
                "Choose 'ollama' or 'azure'."
            )
