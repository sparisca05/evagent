import "./Message.css";

const Message = ({
    text,
    sender,
    timestamp,
    isTyping = false,
}: {
    text: string;
    sender: string;
    timestamp: string;
    isTyping?: boolean;
}) => {
    return (
        <div
            className={`message ${sender}-message ${isTyping ? "typing" : ""}`}
        >
            <div className="message-content">
                {!isTyping ? (
                    <div className="message-text">{text}</div>
                ) : (
                    <div className="typing-indicator">
                        <span className="dot"></span>
                        <span className="dot"></span>
                        <span className="dot"></span>
                    </div>
                )}
                <div className="message-time">{timestamp}</div>
            </div>
        </div>
    );
};

export default Message;
