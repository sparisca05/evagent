import { useState } from "react";
import ExcelJS from "exceljs";

import Chat from "./components/Chat/Chat";
import "./App.css";

function App() {
    const [linkedinUrls, setLinkedinUrls] = useState<string[]>([]);
    const historialChatBot = [];
    const [messages, setMessages] = useState([
        {
            text: "👋 Hola! Soy Isabot, tu Chatbot de Negociación de Pagos.\n Escribe algo para obtener tu estado de cuenta actual.",
            sender: "bot",
            timestamp: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            }),
        },
    ]);
    const [isTyping, setIsTyping] = useState(false);

    const addBotMessage = (text: string) => {
        const newMessage = {
            text,
            sender: "bot",
            timestamp: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            }),
        };
        setMessages((prev) => [newMessage, ...prev]);
    };

    const handleSendMessage = async (message: string) => {
        if (!message.trim()) return;

        // Añadir mensaje del usuario
        const userMessage = {
            text: message,
            sender: "user",
            timestamp: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            }),
        };
        setMessages((prev) => [userMessage, ...prev]);
        setIsTyping(true);

        // Enviar mensaje al bot

        for await (const chunk of response) {
            const text = chunk.text;
            if (text) {
                accumulatedResponse += text; // Accumulate the chunks
            }
        }

        setIsTyping(false);

        // Add the complete response as a single message
        if (accumulatedResponse) {
            addBotMessage(accumulatedResponse);
        }

        // Añadir respuesta del bot al historial
        historialChatBot.push(accumulatedResponse);
    };

    const handleFileUpload = async (event: any) => {
        const file = event.target.files[0];
        if (file) {
            const workbook = new ExcelJS.Workbook();
            const reader = new FileReader();

            reader.onload = async (e: any) => {
                const buffer = e.target.result;
                await workbook.xlsx.load(buffer);
                const worksheet = workbook.getWorksheet(1);
                const jsonData: Array<{ [key: string]: any }> = [];

                worksheet?.eachRow((row, rowNumber) => {
                    jsonData.push(row.values);
                });

                console.log("Datos cargados:", jsonData);
                // Extract LinkedIn URLs from the uploaded data
                const extractedUrls = jsonData
                    .map((row) => row.linkedinUrl)
                    .filter(Boolean);
                console.log("LinkedIn URLs:", extractedUrls);
                setLinkedinUrls(extractedUrls);
            };
            reader.readAsArrayBuffer(file);
        }
    };

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="header-content">
                    <div className="logo">
                        <div className="logo-icon">EVA</div>
                        <div className="logo-text">
                            <h1>Evagent</h1>
                            <p>Find your potential customers</p>
                        </div>
                    </div>
                    <div className="connection-status">
                        <span className="status-dot"></span>
                        <span>Online</span>
                    </div>
                </div>
            </header>

            {/* Contenido principal */}
            <main className="main-content">
                <div>
                    {/* Sección de carga de archivo */}
                    <section className="file-section">
                        <section className="file-upload-section">
                            <input
                                type="file"
                                draggable
                                accept=".xlsx, .xls"
                                onChange={handleFileUpload}
                            />
                        </section>
                        <button onClick={() => 0}>Process LinkedIn URLs</button>
                    </section>
                    {/* Mostrar invitados filtrados */}
                    <section className="filtered-guests-section">
                        <h2>Invitados Filtrados</h2>
                        <ul></ul>
                    </section>
                </div>

                {/* Sección del Chat */}
                <section className="chat-section">
                    <Chat
                        messages={messages}
                        onSendMessage={handleSendMessage}
                        isTyping={isTyping}
                    />
                </section>
            </main>
        </div>
    );
}

export default App;
