# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import logging
import json
from typing import Callable
from openai import AzureOpenAI
from azure.core.credentials import TokenCredential
from azure.identity import get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from utils import get_azure_credential

def get_prompt(
    prompt: str,
    path: str = "prompts/"
) -> str:
    """
    Load prompt.
    """
    with open(path + prompt, 'r') as fp:
        content = fp.read()
    return content


RAG_GROUNDING_PROMPT = get_prompt("rag_grounding.txt")


class AOAIClient(AzureOpenAI):
    """
    Chat-only AOAI Client.

    AzureOpenAI wrapper with function-calling and RAG support.
    """

    def __init__(
        self,
        endpoint: str,
        deployment: str,
        api_version: str = "2023-12-01-preview",
        scope: str = "https://cognitiveservices.azure.com/.default",
        azure_credential: TokenCredential = None,
        system_message: str = None,
        function_calling: bool = False,
        tools: list = None,
        functions: dict[str, Callable] = None,
        return_functions: bool = False,
        use_rag: bool = False,
        search_client: SearchClient = None
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        if not azure_credential:
            azure_credential = get_azure_credential()
        token_provider = get_bearer_token_provider(azure_credential, scope)
        AzureOpenAI.__init__(
            self,
            api_version=api_version,
            azure_ad_token_provider=token_provider,
            azure_endpoint=endpoint
        )

        # Function-calling:
        self.function_calling = function_calling
        self.tools = tools
        self.functions = functions
        self.return_functions = return_functions

        # RAG:
        self.use_rag = use_rag
        self.search_client = search_client

        # General:
        self.deployment = self.model_name = deployment
        self.api_version = api_version
        self.chat_api = True
        self.messages = []

        if system_message:
            # Prepend system message:
            self.messages = [{"role": "system", "content": system_message}]

    def call_functions(
        self,
        language: str,
        id: str
    ) -> list:
        """
        AOAI function calling.

        Returns function-call responses.
        """
        # Call chat API with function-calling enabled:
        response = self.chat.completions.create(
            model=self.deployment,
            messages=self.messages,
            tools=self.tools,
            tool_choice="auto",
        )

        # Process model's response:
        response_message = response.choices[0].message
        self.messages.append(response_message)
        self.logger.info(f"Model response: {response_message}")

        # Handle function calls:
        function_responses = []
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                self.logger.info(f"Function call: {function_name}")
                self.logger.info(f"Function arguments: {function_args}")

                if function_name in self.functions:
                    # All functions require single extracted parameter:
                    func_input = next(iter(function_args.values()))
                    func = self.functions[function_name]
                    func_response = func(func_input, language, id)
                else:
                    func_response = json.dumps({"error": "Unknown function"})

                function_responses.append(func_response)
                self.logger.info(f"Function response: {str(func_response)}")
                self.messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(func_response)
                })
        else:
            self.logger.info("No tool calls made by model.")

        return function_responses

    def generate_rag_prompt(
        self,
        query: str
    ) -> tuple[str, str]:
        """
        Generates RAG grounding prompt given query and search client.
        Returns (system_prompt, user_prompt) tuple.
        """
        self.logger.info("Calling search client")
        vector_query = VectorizableTextQuery(
            text=query,
            k_nearest_neighbors=50,
            fields="text_vector"
        )
        search_results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["title", "chunk"],
            top=5
        )

        sources_formatted = "=================\n".join(
            [f'TITLE: {doc["title"]}, CONTENT: {doc["chunk"]}' for doc in search_results]
        )

        # Split the RAG prompt into system and user parts
        full_prompt = RAG_GROUNDING_PROMPT.format(
            query=query,
            sources=sources_formatted
        )
        
        # Extract system part (everything before # Query)
        system_part = full_prompt.split("# Query")[0].strip()
        
        # Extract user part (Query and Sources sections)
        user_part = full_prompt.split("# Query")[1].strip() if "# Query" in full_prompt else f"# Query\n{query}\n\n# Sources\n{sources_formatted}"

        return system_part, user_part

    def chat_completion(
        self,
        message: str,
        language: str = None,
        id: str = None,
        history: list = None,
        use_rag: bool | None = None,
        function_calling: bool | None = None,
        response_format: dict | None = None
    ) -> str:
        """
        AOAI chat completion with conversation history.
        """
        # Initialize messages with system prompt and conversation history
        messages = []
        
        # Add system message if available
        if hasattr(self, 'messages') and self.messages and self.messages[0].get('role') == 'system':
            messages.append(self.messages[0])
        
        # Add conversation history if provided
        if history:
            for msg in history:
                # Convert ChatMessage to OpenAI format
                role = "assistant" if msg.role.lower() in ["system", "assistant"] else "user"
                messages.append({"role": role, "content": msg.content})
        
        # Add current user message:
        effective_use_rag = self.use_rag if use_rag is None else use_rag
        if effective_use_rag:
            # For RAG, split into system and user messages for better instruction following
            system_prompt, user_prompt = self.generate_rag_prompt(message)
            # Add system prompt as system message (overrides any existing system message)
            messages = [{"role": "system", "content": system_prompt}]
            # Re-add conversation history after system message
            if history:
                for msg in history:
                    role = "assistant" if msg.role.lower() in ["system", "assistant"] else "user"
                    messages.append({"role": role, "content": msg.content})
            # Add user prompt as user message
            messages.append({"role": "user", "content": user_prompt})
        else:
            messages.append({"role": "user", "content": message})

        effective_function_calling = self.function_calling if function_calling is None else function_calling
        if effective_function_calling:
            # For function calling, use the instance messages
            self.messages = messages
            function_results = self.call_functions(language=language, id=id)
            if self.return_functions:
                # Return function-call results directly:
                return function_results

        # Call chat API with full conversation context:
        try:
            kwargs = {"model": self.deployment, "messages": messages}
            if response_format is not None:
                kwargs["response_format"] = response_format

            try:
                self.logger.info(f"Attempting chat completion with kwargs: {kwargs}")
                response = self.chat.completions.create(**kwargs)
            except Exception as e:
                self.logger.warning(
                    f"Initial chat completion call failed with error: {e}. "
                    "Retrying without response_format if it was used."
                )
                if "response_format" in kwargs:
                    kwargs.pop("response_format")
                    self.logger.info(f"Retrying chat completion with kwargs: {kwargs}")
                    response = self.chat.completions.create(**kwargs)
                else:
                    # If response_format wasn't the issue, re-raise the original error
                    raise

            response_message = response.choices[0].message
            self.logger.info(f"Model response: {response_message}")
            return response_message.content
        except Exception as e:
            # Log minimal context to help debug upstream callers
            snippet = message[:400] if isinstance(message, str) else str(message)[:400]
            self.logger.error(f"chat_completion failed definitively: {e} | prompt_snippet={snippet}")
            raise
