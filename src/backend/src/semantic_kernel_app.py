# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
import json
import logging
import pii_redacter
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
# Removed unused imports for direct RAG mode
# from semantic_kernel_orchestrator import SemanticKernelOrchestrator
# from azure.identity.aio import DefaultAzureCredential
# from semantic_kernel.agents import AzureAIAgent
from utils import get_azure_credential
from aoai_client import AOAIClient, get_prompt
from azure.search.documents import SearchClient
from appointment_orchestrator import AppointmentOrchestrator

from typing import List

# Run locally with `uvicorn app:app --reload --host 127.0.0.1 --port 7000`
# Comment out for local testing:
# from dotenv import load_dotenv
# load_dotenv()


class ChatMessage(BaseModel):
    role: str
    content: str


# Initialize structure for holding chat requests
class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]


# Environment variables for direct RAG mode
MODEL_NAME = os.environ.get("AOAI_DEPLOYMENT")
print(f"Using MODEL_NAME: {MODEL_NAME} for direct RAG mode")

# Comment out for local testing:
# AGENT_IDS = {
#     "TRIAGE_AGENT_ID": os.environ.get("TRIAGE_AGENT_ID"),
#     "HEAD_SUPPORT_AGENT_ID": os.environ.get("HEAD_SUPPORT_AGENT_ID"),
#     "ORDER_STATUS_AGENT_ID": os.environ.get("ORDER_STATUS_AGENT_ID"),
#     "ORDER_CANCEL_AGENT_ID": os.environ.get("ORDER_CANCEL_AGENT_ID"),
#     "ORDER_REFUND_AGENT_ID": os.environ.get("ORDER_REFUND_AGENT_ID"),
#     "TRANSLATION_AGENT_ID": os.environ.get("TRANSLATION_AGENT_ID"),
# }

# Skip agent ID validation - using direct RAG mode
print("Direct RAG mode enabled - skipping agent orchestration setup")

DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist"))
# log dist_dir
print(f"DIST_DIR: {DIST_DIR}")


# Initialize the Azure Search client
search_client = SearchClient(
    endpoint=os.environ.get("SEARCH_ENDPOINT"),
    index_name=os.environ.get("SEARCH_INDEX_NAME"),
    credential=get_azure_credential()
)
print("Search client initialized.")

# RAG AOAI client:
rag_client = AOAIClient(
    endpoint=os.environ.get("AOAI_ENDPOINT"),
    deployment=os.environ.get("AOAI_DEPLOYMENT"),
    use_rag=True,
    search_client=search_client
)
print("RAG client initialized.")

# Extract-utterances AOAI client:
extract_prompt = get_prompt("extract_utterances.txt")
extract_client = AOAIClient(
    endpoint=os.environ.get("AOAI_ENDPOINT"),
    deployment=os.environ.get("AOAI_DEPLOYMENT"),
    system_message=extract_prompt
)

# Intent recognition client:
intent_prompt = get_prompt("intent_recognition.txt")
intent_client = AOAIClient(
    endpoint=os.environ.get("AOAI_ENDPOINT"),
    deployment=os.environ.get("AOAI_DEPLOYMENT"),
    system_message=intent_prompt
)

# PII:
PII_ENABLED = os.environ.get("PII_ENABLED", "false").lower() == "true"
print(f"PII_ENABLED: {PII_ENABLED}")

# Appointment orchestrator:
appointment_orchestrator = AppointmentOrchestrator(rag_client)
print("Appointment orchestrator initialized.")


# Fallback function (RAG) definition:
def fallback_function(
    query: str,
    language: str,
    id: int,
    history: list[ChatMessage] = None
) -> str:
    """
    Call RAG client for grounded chat completion with conversation history.
    """
    if PII_ENABLED:
        # Redact PII:
        query = pii_redacter.redact(
            text=query,
            id=id,
            language=language,
            cache=True
        )

    return rag_client.chat_completion(query, history=history)


async def get_intent(message: str, history: list[ChatMessage]) -> str:
    """Classify user intent using LLM."""
    try:
        # Pass conversation history for context
        history_str = ", ".join(f"{msg.role} - {msg.content}" for msg in history)
        contextual_message = f"History: [{history_str}]\n\nUser Message: {message}"

        raw_response = intent_client.chat_completion(contextual_message, history=None) # history is already included
        print(f"Intent raw response: {raw_response}")
        
        json_response = json.loads(raw_response)
        intent = json_response.get("intent", "CONSULTATION") # Default to consultation on error
        print(f"Detected intent: {intent}")
        return intent
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Error decoding intent JSON: {e}")
        # If JSON parsing fails, fall back to keyword-based check as a safety net
        if appointment_orchestrator.is_booking_request(message):
             return "BOOKING"
        return "CONSULTATION"
    except Exception as e:
        logging.error(f"Error getting intent: {e}")
        return "CONSULTATION" # Default to consultation on any other error

# Enhanced function for medical consultation with appointment booking
async def orchestrate_chat(
    message: str,
    history: list[ChatMessage],
    chat_id: int
) -> tuple[list[str], bool]:

    responses = []
    need_more_info = False

    # Reshaping system input into proper backend format
    task = f"query: {message}"

    history_str = ", ".join(f"{msg.role} - {msg.content}" for msg in history)
    if history_str:
        task = f"query: {message}, {history_str}"

    print(f"Processing message: {task} with chat_id: {chat_id}")
    try:
        # Handle PII redaction if enabled
        if PII_ENABLED:
            print(f"Redacting PII for message: {task} with chat_id: {chat_id}")
            task = pii_redacter.redact(
                text=task,
                id=chat_id,
                cache=True
            )

        try:
            # Determine intent first
            intent = await get_intent(message, history)

            # STATE 1: User wants to book or is in a booking process
            if intent == "BOOKING":
                booking_info = appointment_orchestrator.appointment_service.get_booking_info(str(chat_id))
                
                # If already in booking process, continue
                if booking_info:
                    print(f"Continuing booking process for message: {message}")
                    response, booking_complete = appointment_orchestrator.process_booking_message(str(chat_id), message)
                    responses.append(response)
                    need_more_info = not booking_complete
                # If starting a new booking process
                else:
                    print(f"Booking request detected: {message}")
                    consultation_text = _extract_consultation_from_history(history)
                    last_assistant_msg = _get_last_assistant_message(history)

                    # If no specific consultation text is found, but the last message was from the assistant,
                    # we can infer that the user is responding to a prompt (most likely a booking offer).
                    if not consultation_text and last_assistant_msg:
                        print("Consultation text not found, but last message was from assistant. Assuming booking context.")
                        # The last assistant message itself is the best available summary.
                        consultation_text = last_assistant_msg
                    
                    if consultation_text:
                        response, booking_complete = appointment_orchestrator.handle_booking_request(str(chat_id), consultation_text, message)
                        responses.append(response)
                        need_more_info = not booking_complete
                    else:
                        # This case now only happens if a user starts the conversation with a booking request.
                        # Treat it as a direct booking.
                        print("Direct booking request inferred on the first turn.")
                        consultation_text = f"사용자가 직접 예약을 요청했습니다: '{message}'"
                        response, booking_complete = appointment_orchestrator.handle_booking_request(str(chat_id), consultation_text, message)
                        responses.append(response)
                        need_more_info = not booking_complete

            # STATE 2: User wants medical consultation
            else: # intent == "CONSULTATION"
                print(f"Consultation intent detected: processing medical consultation for: {message}")
                response = fallback_function(
                    message,
                    "ko",
                    chat_id,
                    history
                )
                need_more_info = True
                responses.append(response)

        except Exception as e:
            logging.error(f"Error processing utterance: {e}")
            responses.append("I encountered an error processing part of your message.")

    except Exception as e:
        logging.error(f"Error in message processing: {e}")
        responses = ["I apologize, but I'm having trouble processing your request. Please try again."]

    finally:
        # Clean up PII cache if enabled
        if PII_ENABLED:
            pii_redacter.remove(id=chat_id)

    return responses, need_more_info


def _extract_consultation_from_history(history: list[ChatMessage]) -> str:
    """대화 히스토리에서 의료 상담 내용 추출"""
    consultation_parts = []
    for msg in history:
        if msg.role == "assistant":
            # 구조화된 상담 내용 찾기
            if any(keyword in msg.content for keyword in ["추정진단", "권장 검사", "치료 및 처치", "의료진 연계", "환자교육", "예후"]):
                consultation_parts.append(msg.content)
            # 예약 제안 메시지도 상담 내용으로 간주 (마크다운 볼드 처리 고려)
            elif "예약을 잡아드릴까요" in msg.content:
                consultation_parts.append(msg.content)
    
    result = "\n".join(consultation_parts) if consultation_parts else ""
    print(f"[DEBUG] Extracted consultation from history: {result}")
    return result

def _get_last_assistant_message(history: list[ChatMessage]) -> str:
    """마지막 어시스턴트 메시지 반환"""
    for msg in reversed(history):
        if msg.role == "assistant":
            return msg.content
    return ""

def _extract_consultation_from_booking_offer(booking_offer_msg: str) -> str:
    """예약 제안 메시지에서 상담 내용 추출"""
    # 예약 제안 메시지가 나왔다는 것은 이미 상담이 완료되었다는 의미
    # 간단한 상담 요약을 생성
    lines = booking_offer_msg.split('\n')
    consultation_summary = []
    
    for line in lines:
        if any(keyword in line for keyword in ["추정진단", "권장 검사", "치료 및 처치", "의료진 연계", "환자교육", "예후"]):
            consultation_summary.append(line)
    
    if consultation_summary:
        return "\n".join(consultation_summary)
    else:
        # 상담 내용이 명확하지 않으면 기본 상담 완료 메시지
        return "의료 상담이 완료되었습니다. 전문의 진료가 필요한 상황입니다."


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Simple setup for direct RAG mode
    try:
        logging.basicConfig(level=logging.WARNING)
        print("Direct RAG mode - simplified startup without agent orchestration")
        
        # Store minimal app state for direct RAG mode
        app.state.direct_rag_mode = True
        
        # Yield control back to FastAPI lifespan
        yield

    except Exception as e:
        logging.error(f"Error during setup: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")


# In order to test uvicorn app locally:
# 1) run `npm run build` in the frontend directory to generate the static files
# 2) move the `dist` directory to `src/backend/src/`
@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(DIST_DIR, "index.html"))


# Define the chat endpoint
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Enhanced mode with appointment booking
        responses, need_more_info = await orchestrate_chat(request.message, request.history, chat_id=0)
        print("[APP]: Response generated, need_more_info:", need_more_info)
        return JSONResponse(
            content={
                "messages": responses,
                "need_more_info": need_more_info
            }, status_code=200)

    except Exception as e:
        logging.error(f"Error in chat endpoint: {e}")
        return JSONResponse(
            content={"error": "An unexpected error occurred"},
            status_code=500
        )


# Define the appointment lookup endpoint
@app.get("/appointment/{appointment_id}")
async def get_appointment(appointment_id: str):
    try:
        appointment = appointment_orchestrator.appointment_service.get_appointment(appointment_id)
        if not appointment:
            return JSONResponse(
                content={"error": "Appointment not found"},
                status_code=404
            )
        
        return JSONResponse(
            content={
                "appointment_id": appointment.appointment_id,
                "patient_name": appointment.patient_name,
                "department": appointment.department,
                "appointment_date": appointment.preferred_date,
                "appointment_time": appointment.preferred_time,
                "status": appointment.status,
                "created_at": appointment.created_at.isoformat()
            },
            status_code=200
        )
    
    except Exception as e:
        logging.error(f"Error in appointment lookup: {e}")
        return JSONResponse(
            content={"error": "An unexpected error occurred"},
            status_code=500
        )


# Define the appointment cancellation endpoint
@app.post("/appointment/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str):
    try:
        success = appointment_orchestrator.appointment_service.cancel_appointment(appointment_id)
        if not success:
            return JSONResponse(
                content={"error": "Appointment not found"},
                status_code=404
            )
        
        return JSONResponse(
            content={"message": "Appointment cancelled successfully"},
            status_code=200
        )
    
    except Exception as e:
        logging.error(f"Error in appointment cancellation: {e}")
        return JSONResponse(
            content={"error": "An unexpected error occurred"},
            status_code=500
        )
