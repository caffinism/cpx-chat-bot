// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
import { useState } from 'react';
import './App.css';
import Chat from './Chat.jsx';
import AppointmentLookup from './AppointmentLookup.jsx';

const App = () => {
  document.documentElement.lang = 'ko';
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('intro');

  const toggleChat = () => {
    setIsChatOpen(!isChatOpen);
  };

  return (
    <div className="hospital-website">
      {/* Top Banner */}
      <div className="top-banner">
        <div className="banner-content">
          <span>📞 응급실: 119 | 대표번호: 02-1234-5678 | 24시간 응급의료센터 운영</span>
        </div>
      </div>

      {/* Navigation Header */}
      <header className="hospital-header">
        <div className="header-container">
          <div className="logo-section">
            <h1>스콧 의료원</h1>
            <p className="hospital-slogan">믿음과 정성으로 함께하는 건강파트너</p>
          </div>
          <nav className="main-nav">
            <ul>
              <li><a href="#" className={activeTab === 'intro' ? 'active' : ''} onClick={(e) => { e.preventDefault(); setActiveTab('intro'); }}>병원소개</a></li>
              <li><a href="#" className="">의료진소개</a></li>
              <li><a href="#" className="">진료과목</a></li>
              <li><a href="#" className={activeTab === 'appointment' ? 'active' : ''} onClick={(e) => { e.preventDefault(); setActiveTab('appointment'); }}>예약조회</a></li>
              <li><a href="#" className="">오시는길</a></li>
            </ul>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Appointment Lookup Section */}
        {activeTab === 'appointment' && (
          <section id="appointment" className="appointment-section">
            <AppointmentLookup />
          </section>
        )}

        {/* Hospital Introduction Section */}
        {activeTab === 'intro' && (
        <section id="intro" className="hospital-intro">
          <div className="intro-container">
            <div className="intro-text">
              <h2>스콧 의료원을 소개합니다</h2>
              <p className="intro-description">
                스콧 의료원은<br/>
                최첨단 의료장비와 풍부한 임상경험을 바탕으로<br/>
                환자 중심의 양질의 의료서비스를 제공하고 있습니다.
              </p>
              <div className="hospital-stats">
                <div className="stat-item">
                  <h3>5개</h3>
                  <p>전문 진료과</p>
                </div>
                <div className="stat-item">
                  <h3>20명</h3>
                  <p>전문의료진</p>
                </div>
                <div className="stat-item">
                  <h3>50병상</h3>
                  <p>입원 시설</p>
                </div>
                <div className="stat-item">
                  <h3>24시간</h3>
                  <p>응급의료센터</p>
                </div>
              </div>
            </div>
            <div className="intro-image">
              <div className="hospital-building">
                <p>본관 7층 건물</p>
              </div>
            </div>
          </div>
        </section>
        )}

        {/* Quick Menu - 병원소개 탭에서만 표시 */}
        {activeTab === 'intro' && (
          <>
            <section className="quick-menu">
              <div className="quick-container">
                <div className="quick-item">
                  <h4>온라인 예약</h4>
                  <p>간편하게 진료예약</p>
                </div>
                <div className="quick-item">
                  <h4>검사결과 조회</h4>
                  <p>진료결과 확인</p>
                </div>
                <div className="quick-item">
                  <h4>처방전 발급</h4>
                  <p>약국 연계서비스</p>
                </div>
                <div className="quick-item ai-consultation">
                  <h4>AI 의료상담</h4>
                  <p>24시간 즉시상담</p>
                </div>
              </div>
            </section>

            {/* Departments Preview */}
            <section className="departments-preview">
              <div className="section-container">
                <h2>주요 진료과목</h2>
                <div className="departments-grid">
                  <div className="dept-card">
                    <h3>내과</h3>
                    <p>소화기, 순환기, 호흡기, 내분비 질환 전문 진료</p>
                    <ul>
                      <li>• 위내시경, 대장내시경</li>
                      <li>• 심전도, 심초음파</li>
                      <li>• 당뇨, 고혈압 관리</li>
                    </ul>
                  </div>
                  <div className="dept-card">
                    <h3>정형외과</h3>
                    <p>근골격계 질환 전문 진료 및 수술</p>
                    <ul>
                      <li>• 관절, 척추 수술</li>
                      <li>• 스포츠 손상 치료</li>
                      <li>• 재활 치료</li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="hospital-footer">
        <div className="footer-container">
          <div className="footer-info">
            <h3>스콧 의료원</h3>
            <p>주소: 서울특별시 강남구 의료원로 123 (우: 06234)</p>
            <p>대표번호: 02-1234-5678 | 응급실: 119</p>
            <p>진료시간: 평일 09:00~18:00, 토요일 09:00~13:00</p>
            <p className="footer-notice">본 AI 상담은 의료 참고용이며, 응급상황 시 즉시 응급실을 방문하세요.</p>
          </div>
        </div>
      </footer>

      {/* Fixed Floating Chat Button */}
      <button 
        className={`floating-chat-button ${isChatOpen ? 'chat-open' : ''}`}
        onClick={toggleChat}
        aria-label="AI 의료 상담 챗봇"
      >
        {isChatOpen ? '✕' : '💬'}
        {!isChatOpen && <span className="chat-pulse"></span>}
      </button>

      {/* Chat Modal */}
      {isChatOpen && (
        <div className="chat-modal">
          <div className="chat-modal-header">
            <h3>🩺 AI 의료 상담</h3>
            <button 
              className="chat-close-button"
              onClick={toggleChat}
            >
              ✕
            </button>
          </div>
          <div className="chat-modal-content">
            <Chat />
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
