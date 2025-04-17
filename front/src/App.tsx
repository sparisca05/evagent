import { useState } from "react";
import axios from "axios";

import Chat from "./components/Chat/Chat";
import "./App.css";

// Generate a unique session ID
const sessionId = `session-${Date.now()}-${Math.random().toString(36)}`;

function App() {
    const [linkedinUrls, setLinkedinUrls] = useState<string[]>();
    const [filePlaceholder, setFilePlaceholder] = useState(
        "Drag and drop a file or click to select"
    );

    const handleFileUpload = async (event: any) => {
        const file = event.target.files
            ? event.target.files[0]
            : event.dataTransfer.files[0];
        if (file) {
            setFilePlaceholder(file.name); // Update placeholder with file name
            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await axios.post(
                    "http://localhost:8000/upload_excel/",
                    formData,
                    {
                        headers: {
                            "Content-Type": "multipart/form-data",
                        },
                    }
                );

                console.log(
                    "Response from backend:",
                    response.data.linkedin_data
                );
                // Extract LinkedIn data from the response
                const extractedData = response.data.linkedin_data;
                setLinkedinUrls(
                    extractedData.map((item: any) => item.linkedinUrl)
                );
            } catch (error) {
                console.error("Error uploading file:", error);
            }
        }
    };

    const handleProcessLinkedinUrls = async () => {
        console.log("Processing LinkedIn URLs...");
        try {
            const response = await axios.post(
                "http://localhost:8000/process_invitees/",
                { session_id: sessionId },
                {
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );
            console.log("Response from agent:", response.data);
        } catch (error) {
            console.error("Error processing LinkedIn URLs:", error);
        }
    };

    return (
        <div className="app">
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
            <main className="main-content">
                <div>
                    <section className="file-section">
                        <h2>Upload a file with invitees profiles</h2>
                        <section className="file-upload-section">
                            <label className="file-upload-label">
                                <span className="file-icon">📁</span>
                                <input
                                    name="file"
                                    type="file"
                                    draggable
                                    accept=".xlsx, .xls"
                                    onDrop={(e) => {
                                        e.preventDefault();
                                        handleFileUpload(e);
                                    }}
                                    onDragOver={(e) => e.preventDefault()}
                                    onChange={handleFileUpload}
                                />
                                <span>{filePlaceholder}</span>
                            </label>
                        </section>
                        <h2>Extracted LinkedIn URLs</h2>
                        <ul>
                            {linkedinUrls !== undefined ? (
                                linkedinUrls.map((url, index) => (
                                    <li key={index}>
                                        <a href={url} target="_blank">
                                            {url}
                                        </a>
                                    </li>
                                ))
                            ) : (
                                <li>No LinkedIn URLs found.</li>
                            )}
                        </ul>
                        <button onClick={handleProcessLinkedinUrls}>
                            Process LinkedIn URLs
                        </button>
                        <section className="filtered-guests-section">
                            <h2>Filtered Emails</h2>
                            <ul></ul>
                        </section>
                    </section>
                </div>
                <section className="chat-section">
                    <Chat sessionId={sessionId} />
                </section>
            </main>
        </div>
    );
}

export default App;
