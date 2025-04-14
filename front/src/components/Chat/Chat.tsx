import { useState, useRef } from "react";
import Message from "../Message/Message";
import "./Chat.css";

const Chat = ({ messages, onSendMessage, isTyping }: any) => {
    const [inputValue, setInputValue] = useState("");
    const messagesEndRef = useRef(null);

    const handleSubmit = (e: any) => {
        e.preventDefault();
        if (inputValue.trim()) {
            onSendMessage(inputValue);
            setInputValue("");
        }
    };

    return (
        <div className="chat">
            <div className="messages-container" ref={messagesEndRef}>
                {isTyping && (
                    <Message
                        text="Escribiendo..."
                        sender="bot"
                        timestamp="Ahora"
                        isTyping
                    />
                )}

                {messages.map((message: any, index: number) => (
                    <Message
                        key={index}
                        text={message.text}
                        sender={message.sender}
                        timestamp={message.timestamp}
                    />
                ))}
            </div>

            <form onSubmit={handleSubmit} className="message-form">
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Escribe tu mensaje..."
                    autoFocus
                />
                <button type="submit">
                    <svg viewBox="0 0 24 24" width="24" height="24">
                        <path
                            fill="currentColor"
                            d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"
                        ></path>
                    </svg>
                </button>
            </form>
        </div>
    );
};

export default Chat;
