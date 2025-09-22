from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class AppointmentResponse(BaseModel):
    appointment_id: str = Field(..., description="예약번호")
    patient_name: str = Field(..., description="환자 성명")
    department: str = Field(..., description="진료과")
    appointment_date: str = Field(..., description="예약 날짜")
    appointment_time: str = Field(..., description="예약 시간")
    status: AppointmentStatus = Field(..., description="예약 상태")
    created_at: datetime = Field(..., description="예약 생성 시간")

class BookingInfo(BaseModel):
    """예약 정보 수집을 위한 중간 상태"""
    patient_name: Optional[str] = None
    phone_number: Optional[str] = None
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    department: Optional[str] = None
    consultation_summary: Optional[str] = None
    
    def is_complete(self) -> bool:
        """모든 필수 정보가 수집되었는지 확인"""
        return all([self.patient_name, self.phone_number, self.preferred_date, self.preferred_time])
    
    def to_summary_string(self) -> str:
        """수집된 정보를 요약 문자열로 변환"""
        summary = []
        if self.patient_name:
            summary.append(f"  - 이름: {self.patient_name}")
        if self.phone_number:
            summary.append(f"  - 연락처: {self.phone_number}")
        if self.preferred_date:
            summary.append(f"  - 희망 날짜: {self.preferred_date}")
        if self.preferred_time:
            summary.append(f"  - 희망 시간: {self.preferred_time}")
        
        if not summary:
            return "  - 아직 수집된 정보가 없습니다."
        return "\n".join(summary)
    
    def to_appointment_request(self) -> 'AppointmentRequest':
        """BookingInfo를 AppointmentRequest로 변환"""
        if not self.is_complete():
            raise ValueError("Incomplete booking information")
        
        return AppointmentRequest(
            patient_name=self.patient_name,
            phone_number=self.phone_number,
            preferred_date=self.preferred_date,
            preferred_time=self.preferred_time,
            department=self.department,
            consultation_summary=self.consultation_summary or ""
        )


class AppointmentRequest(BaseModel):
    """예약 완료 시 생성되는 모델"""
    appointment_id: Optional[str] = Field(None, description="예약번호")
    patient_name: str = Field(..., description="환자 성명")
    phone_number: str = Field(..., description="연락처")
    preferred_date: str = Field(..., description="희망 날짜")
    preferred_time: str = Field(..., description="희망 시간")
    department: str = Field(..., description="진료과")
    consultation_summary: str = Field(..., description="상담 내용 요약")
    symptoms: List[str] = Field(default=[], description="주요 증상")
    diagnosis: str = Field(default="", description="추정 진단")
    recommendations: str = Field(default="", description="권장사항")
    created_at: datetime = Field(default_factory=datetime.now)
    status: AppointmentStatus = Field(default=AppointmentStatus.PENDING)
