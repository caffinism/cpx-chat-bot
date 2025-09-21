// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
import { useState, useEffect, useRef } from 'react';
import Markdown from 'react-markdown'

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [needMoreInfo, setNeedMoreInfo] = useState(false);
    const [isWelcomeStreaming, setIsWelcomeStreaming] = useState(false);
    const [streamedWelcome, setStreamedWelcome] = useState('');

    const messageEndRef = useRef(null);
    const welcomeMessage = `안녕하세요! 의료 상담 AI입니다. 🩺

어떤 증상으로 도움이 필요하신가요? 

**필요한 정보:**
• 성별, 나이
• 언제부터, 어디가, 어떻게 아픈지

편하게 말씀해 주세요! 💬`;

    // Welcome message streaming effect
    useEffect(() => {
        if (messages.length === 0) {
            setIsWelcomeStreaming(true);
            setStreamedWelcome('');
            
            const streamText = async () => {
                // Wait 1 second before starting
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                for (let i = 0; i <= welcomeMessage.length; i++) {
                    setStreamedWelcome(welcomeMessage.slice(0, i));
                    await new Promise(resolve => setTimeout(resolve, 30)); // 30ms per character
                }
                setIsWelcomeStreaming(false);
            };
            
            streamText();
        }
    }, [messages.length]);

    const scrollToBottom = () => {
        messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const createSystemInput = (userMessageContent) => {

        // Send last 14 messages to maintain conversation context (7 user + 7 system)
        const historyMessages = messages.slice(-14);
        console.log("Sending history messages:", historyMessages);

        return {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                message: userMessageContent,
                history: historyMessages,
            })
        };
    };

    const parseSystemResponse = (systemResponse) => {
        return {
            messages: systemResponse["messages"] || [],
            needMoreInfo: systemResponse["need_more_info"] || false
        };
    };

    const chatWithSystem = async (userMessageContent) => {
        try {
            const response = await fetch(
                `/chat`,
                createSystemInput(userMessageContent)
            );

            if (!response.ok) {
                throw new Error("Oops! Bad chat response.");
            }

            const systemResponse = await response.json();
            const { messages, needMoreInfo } = parseSystemResponse(systemResponse);

            console.log("System messages:", messages);
            setNeedMoreInfo(needMoreInfo);

            return { messages };
        } catch (error) {
            console.error("Error while processing chat: ", error);
            return { messages: [] };
        }
    };

    const handleSendMessage = async (userMessageContent) => {
        setMessages((prevMessages) => [
            ...prevMessages, { role: "User", content: userMessageContent }
        ]);

        setIsTyping(true);
        const { messages: systemMessages } = await chatWithSystem(userMessageContent);
        setIsTyping(false);

        for (const msg of systemMessages) {
            setMessages((prevMessages) => [
                ...prevMessages, 
                { role: "System", content: msg }
            ]);
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {messages.length === 0 && (
                    <div className="message agent">
                        <div className="message-content">
                            <h3 className="message-header">🩺 의사</h3>
                            <div className="message-text streaming">
                                <Markdown>{streamedWelcome || ''}</Markdown>
                                {isWelcomeStreaming && <span className="cursor">|</span>}
                            </div>
                        </div>
                    </div>
                )}
                {messages.map((message, index) => (
                    <div key={index} tabIndex="0" className={message.role === 'User' ? "message user" : "message agent"}>
                        <div className="message-content">
                            <h3 className="message-header">{message.role === 'User' ? '👤 환자' : '🩺 의사'}</h3>
                            <Markdown className="message-text">{message.content}</Markdown>
                        </div>
                    </div>
                ))}
                {isTyping && (
                    <div className="message agent">
                        <div className="message-content">
                            <h3 className="message-header">🩺 의사</h3>
                            <p className="typing-indicator">
                                진단 중입니다<span className="dots">...</span>
                            </p>
                        </div>
                    </div>
                )}
                <div ref={messageEndRef}/>
            </div>
            <form
                className="chat-input-form"
                onSubmit={(e) => {
                    e.preventDefault();
                    const input = e.target.input.value;
                    if (input.trim() != "") {
                        handleSendMessage(input);
                        e.target.reset();
                    }
                }}
                aria-label="Chat Input Form"
            >
                <input
                    className="chat-input"
                    type="text"
                    name="input"
                    placeholder="Type your message..."
                    disabled={isTyping}/>
                <button
                    className="chat-submit-button" 
                    type="submit"
                >
                    Send
                </button>
            </form>
        </div>
    );
}

export default Chat;
