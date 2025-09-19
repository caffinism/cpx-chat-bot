// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
import { useState } from 'react';
import './App.css';
import Chat from './Chat.jsx';

const App = () => {
  document.documentElement.lang = 'ko';
  const [isChatOpen, setIsChatOpen] = useState(false);

  const toggleChat = () => {
    setIsChatOpen(!isChatOpen);
  };

  return (
    <div className="page-content-container">
      {/* Hospital Homepage */}
      <div className="hospital-homepage">
        <header className="hospital-header">
          <h1>🏥 스콧 의료원</h1>
          <p className="hospital-subtitle">AI 기반 24시간 의료 상담 서비스</p>
        </header>
        
        <main className="hospital-main">
          <section className="services-section">
            <h2>📋 주요 진료 과목</h2>
            <div className="services-grid">
              <div className="service-card">
                <h3>🫀 내과</h3>
                <p>소화기, 순환기, 호흡기 질환</p>
              </div>
              <div className="service-card">
                <h3>👶 산부인과</h3>
                <p>여성 질환, 임신 관리</p>
              </div>
              <div className="service-card">
                <h3>🧒 소아과</h3>
                <p>소아 질환, 성장 발달</p>
              </div>
              <div className="service-card">
                <h3>🦴 정형외과</h3>
                <p>관절, 뼈, 근육 질환</p>
              </div>
            </div>
          </section>

          <section className="ai-info-section">
            <h2>🤖 AI 의료 상담의 특징</h2>
            <ul>
              <li>✅ 596개 CPX 의료 케이스 기반 정확한 진단</li>
              <li>✅ 24시간 언제든지 의료 상담 가능</li>
              <li>✅ 3번 대화로 신속한 종합 진단</li>
              <li>✅ 전문의 수준의 체계적 문진</li>
            </ul>
          </section>
        </main>

        <footer className="hospital-footer">
          <p>⚠️ 본 서비스는 의료 참고용이며, 응급상황 시 즉시 병원 방문하세요.</p>
        </footer>
      </div>

      {/* Floating Chat Button */}
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
