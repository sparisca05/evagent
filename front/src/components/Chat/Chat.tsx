import { useState, useRef } from "react";
import axios from "axios";
import Message from "../Message/Message";
import "./Chat.css";

const Chat = () => {
    const [inputValue, setInputValue] = useState("");
    const messagesEndRef = useRef(null);
    const [messages, setMessages] = useState([
        {
            text: "👋 Hi there! I'm Eva, your AI Agent that helps you to identify potencial clients for your company or business.",
            sender: "bot",
            timestamp: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            }),
        },
    ]);
    const [isTyping, setIsTyping] = useState(false);

    const handleSubmit = async (e: any) => {
        e.preventDefault();
        setIsTyping(true); // Set typing state to true
        setTimeout(() => setIsTyping(false), 2000); // Simulate typing delay
        if (inputValue.trim()) {
            // Add the user's message to the chat
            const newMessage = {
                text: inputValue,
                sender: "user",
                timestamp: new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                }),
            };
            setMessages((prevMessages: any) => [...prevMessages, newMessage]);

            // Clear the input field
            setInputValue("");

            try {
                // Send the message to the backend
                const response = await axios.post(
                    "http://localhost:8000/chat",
                    { message: inputValue }
                );

                // Add the bot's response to the chat
                const botMessage = {
                    text: response.data.reply,
                    sender: "bot",
                    timestamp: new Date().toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                    }),
                };
                setMessages((prevMessages: any) => [
                    ...prevMessages,
                    botMessage,
                ]);
            } catch (error) {
                console.error("Error sending message to backend:", error);
            }
        }
        setIsTyping(false); // Set typing state to false after processing the message
    };

    return (
        <div className="chat">
            <div className="messages-container" ref={messagesEndRef}>
                {isTyping && (
                    <Message
                        text="Typing..."
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
                    placeholder="Ask something to Eva"
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
