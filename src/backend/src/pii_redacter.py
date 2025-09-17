# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import logging
from azure.ai.textanalytics import TextAnalyticsClient
from utils import get_azure_credential

"""
Azure AI Language PII recognition, redaction, and reconstruction.
"""

CATEGORIES = os.environ.get("PII_CATEGORIES", "").upper().split(",")
CONFIDENCE_THRESHOLD = float(os.environ.get("PII_CONFIDENCE_THRESHOLD", "0.5"))
TA_CLIENT = TextAnalyticsClient(
    endpoint=os.environ.get("LANGUAGE_ENDPOINT"),
    credential=get_azure_credential()
)

entity_id = 0
redaction_mappings = dict()

_logger = logging.getLogger(__name__)


def create_redaction_key(
    category: str
) -> str:
    """
    Create PII entity redaction key.
    """
    global entity_id
    entity_id += 1
    return f"{{PII_{category}_{entity_id}}}"


def apply_mapping(
    text: str,
    id: str,
    redact: bool = True
) -> str:
    """
    Redact or reconstruct text.
    """
    result = text
    mapping = redaction_mappings[id]

    for redaction, entity in mapping.items():
        if redact:
            result = result.replace(entity, redaction)
        else:
            result = result.replace(redaction, entity)

    return result


def recognize(
    text: str,
    id: str,
    language: str = "en",
    cache: bool = True
) -> bool:
    """
    Recognize PII entities in text input and
    create redaction mapping.
    """
    # Call TA:
    response = TA_CLIENT.recognize_pii_entities(
        documents=[text],
        language=language
    )
    result = response[0]
    if result.is_error:
        return []

    # Filter based on confidence and category:
    mapping = dict()
    for ent in result.entities:
        category = ent.category.upper()
        confidence = ent.confidence_score

        if category in CATEGORIES and confidence > CONFIDENCE_THRESHOLD:
            redaction_key = create_redaction_key(category)
            mapping[redaction_key] = ent.text

    if cache:
        # Store mapping:
        redaction_mappings[id] = mapping

    return len(mapping) != 0


def redact(
    text: str,
    id: str,
    language: str = "en",
    cache: bool = True
) -> str:
    """
    Create text redaction.
    """
    if id in redaction_mappings:
        return apply_mapping(
            text=text,
            id=id,
            redact=True
        )

    if not recognize(text=text, id=id, language=language):
        _logger.info("No PII entities found")
        return text

    _logger.info(f"Pre-redaction: {text}")
    result = apply_mapping(
        text=text,
        id=id,
        redact=True
    )

    if not cache:
        # Do not store mapping:
        redaction_mappings.pop(id)

    _logger.info(f"Post-redaction: {result}")
    return result


def reconstruct(
    text: str,
    id: str,
    cache: bool = False
) -> str:
    """
    Reconstruct redacted text.
    """
    if id not in redaction_mappings:
        _logger.warning(f"No mapping for id: {id}")
        return text

    _logger.info(f"Pre-reconstruction: {text}")
    result = apply_mapping(
        text=text,
        id=id,
        redact=False
    )

    if not cache:
        # Clean up memory:
        redaction_mappings.pop(id)

    _logger.info(f"Post-reconstruction: {result}")
    return result


def remove(
    id: str
):
    """
    Remove redaction mapping.
    """
    if id not in redaction_mappings:
        _logger.warning(f"No mapping for id: {id}")
        return

    redaction_mappings.pop(id)
