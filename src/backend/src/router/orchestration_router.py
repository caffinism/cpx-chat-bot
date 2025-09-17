# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import logging
from typing import Callable
from azure.ai.language.conversations import ConversationAnalysisClient
from router.clu_router import parse_response as parse_clu_response
from router.cqa_router import parse_response as parse_cqa_response
from utils import get_azure_credential

_logger = logging.getLogger(__name__)


def create_orchestration_router() -> Callable[[str, str, str], dict]:
    """
    Create Orchestration runtime routing function.
    """
    project_name = os.environ['ORCHESTRATION_PROJECT_NAME']
    deployment_name = os.environ['ORCHESTRATION_DEPLOYMENT_NAME']
    endpoint = os.environ['LANGUAGE_ENDPOINT']
    credential = get_azure_credential()
    client = ConversationAnalysisClient(endpoint, credential)

    def create_input(
        utterance: str,
        language: str,
        id: str
    ) -> dict:
        """
        Create JSON input for Orchestration runtime.
        """
        return {
            "kind": "Conversation",
            "analysisInput": {
                "conversationItem": {
                    "id": str(id),
                    "participantId": "0",
                    "language": language,
                    "text": utterance
                }
            },
            "parameters": {
                "projectName": project_name,
                "deploymentName": deployment_name
            }
        }

    def call_runtime(
        utterance: str,
        language: str,
        id: str
    ) -> dict:
        """
        Call Orchestration runtime.
        """
        input_json = create_input(
            utterance=utterance,
            language=language,
            id=id
        )

        try:
            _logger.info(f"Calling {project_name}:{deployment_name} runtime")

            response = client.analyze_conversation(
                task=input_json
            )

            _logger.info(f"Runtime response: {response}")
            return parse_response(
                response=response
            )

        except Exception as e:
            _logger.error(f"Runtime call failed: {e}")
            return {
                "error": e
            }

    return call_runtime


def parse_response(
    response: dict
) -> dict:
    """
    Parse Orchestration runtime response.
    """
    confidence_threshold = float(os.environ.get("ORCHESTRATION_CONFIDENCE_THRESHOLD", "0.5"))
    prediction = response["result"]["prediction"]
    orch_intent = prediction["topIntent"]
    orch_intent_result = prediction["intents"][orch_intent]
    confidence = orch_intent_result["confidenceScore"]
    error = None

    # Filter based on confidence threshold:
    if confidence < confidence_threshold:
        _logger.warning("Orchestration confidence threshold not met")
        error = "Orchestration confidence threshold not met"

    # Check orchestration routing kind:
    kind = orch_intent_result["targetProjectKind"]
    parsed_result = {}
    if kind == "Conversation":
        parsed_result = parse_clu_response(
            response=orch_intent_result
        )
    elif kind == "QuestionAnswering":
        parsed_result = parse_cqa_response(
            response=orch_intent_result["result"]
        )
    else:
        error = f"Unexpected orchestration intent kind: {kind}"

    if error is not None:
        parsed_result["error"] = error
    parsed_result["api_response"] = response

    return parsed_result
