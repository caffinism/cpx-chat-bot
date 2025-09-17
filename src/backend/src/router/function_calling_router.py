# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import logging
import pii_redacter
from typing import Callable
from azure.core.rest import HttpRequest
from azure.ai.language.conversations.authoring import ConversationAuthoringClient
from azure.ai.language.questionanswering.authoring import AuthoringClient
from aoai_client import AOAIClient, get_prompt
from router.clu_router import create_clu_router
from router.cqa_router import create_cqa_router
from utils import get_azure_credential

_logger = logging.getLogger(__name__)

PII_ENABLED = os.environ.get("PII_ENABLED", "false").lower() == "true"
FUNCTION_CALLING_PROMPT = get_prompt("function_calling.txt")


def get_tools(
    path: str = "tools/"
) -> dict:
    """
    Load AOAI function-calling tool specs.
    """
    tools = []
    for file in os.listdir(path):
        with open(path + file, 'r') as fp:
            tools.append(json.load(fp))
    return tools


def get_clu_intents() -> list[str]:
    """
    Get all intents registered in CLU project.
    """
    project_name = os.environ['CLU_PROJECT_NAME']
    endpoint = os.environ['LANGUAGE_ENDPOINT']
    credential = get_azure_credential()
    client = ConversationAuthoringClient(endpoint, credential)

    try:
        _logger.info(f"Getting intents from project {project_name}")

        poller = client.begin_export_project(
            project_name=project_name,
            string_index_type="Utf16CodeUnit",
            exported_project_format="Conversation"
        )

        job_state = poller.result()
        request = HttpRequest("GET", job_state["resultUrl"])
        response = client.send_request(request)
        exported_project = response.json()

        intents = [
            i["category"] for i in exported_project["assets"]["intents"]
        ]
        intents = list(filter(lambda x: x != "None", intents))
        return intents

    except Exception as e:
        _logger.error(f"Unable to get intents: {e}")
        raise e


def get_cqa_questions() -> list[str]:
    """
    Get all registered questions in CQA project.
    """
    project_name = os.environ['CQA_PROJECT_NAME']
    endpoint = os.environ['LANGUAGE_ENDPOINT']
    credential = get_azure_credential()
    client = AuthoringClient(endpoint, credential)

    try:
        _logger.info(f"Getting questions from project {project_name}")

        poller = client.begin_export(
            project_name=project_name,
            file_format='json'
        )

        job_state = poller.result()
        request = HttpRequest("GET", job_state["resultUrl"])
        response = client.send_request(request)
        exported_project = response.json()

        questions = set()
        for item in exported_project["Assets"]["Qnas"]:
            for q in item["Questions"]:
                questions.add(q)
        return list(questions)

    except Exception as e:
        _logger.error(f"Unable to get questions: {e}")
        raise e


def create_router_hook(
    router: Callable[[str, str, str], dict]
) -> Callable[[str, str, str], dict]:
    """
    Create router hook function.

    Apply PII reconstruction when applicable.
    """
    def route(
        text: str,
        language: str,
        id: str
    ) -> dict:
        if PII_ENABLED:
            # Reconstruct PII:
            text = pii_redacter.reconstruct(
                text=text,
                id=id,
                cache=True
            )
        return router(text, language, id)

    return route


def create_function_calling_router() -> Callable[[str, str, str], dict]:
    """
    Create function-calling router.
    """
    functions = {
        "get_clu": create_router_hook(
            router=create_clu_router()
        ),
        "get_cqa": create_router_hook(
            router=create_cqa_router()
        )
    }

    clu_intents = get_clu_intents()
    cqa_questions = get_cqa_questions()

    prompt = FUNCTION_CALLING_PROMPT.format(
        intents=", ".join(clu_intents),
        questions="\n".join(cqa_questions)
    )

    aoai_client = AOAIClient(
        endpoint=os.environ['AOAI_ENDPOINT'],
        deployment=os.environ['AOAI_DEPLOYMENT'],
        system_message=prompt,
        function_calling=True,
        tools=get_tools(),
        functions=functions,
        return_functions=True
    )

    def function_calling_router(
        message: str,
        language: str,
        id: str
    ) -> dict:
        """
        Function-calling router function.
        """
        if PII_ENABLED:
            # Redact PII:
            message = pii_redacter.redact(
                text=message,
                id=id,
                language=language,
                cache=True
            )

        function_results = aoai_client.chat_completion(
            message=message,
            language=language,
            id=id
        )

        # There should only be one function-call:
        if len(function_results) != 1:
            return {
                "error": "No function call made"
            }

        parsed_response = function_results[0]
        return parsed_response

    return function_calling_router
