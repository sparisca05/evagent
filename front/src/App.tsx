import { useState } from "react";
import axios from "axios";

import Chat from "./components/Chat/Chat";
import "./App.css";

function App() {
    const [linkedinUrls, setLinkedinUrls] = useState<string[]>();

    const handleFileUpload = async (event: any) => {
        const file = event.target.files[0];
        if (file) {
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
                        <section className="file-upload-section">
                            <input
                                type="file"
                                draggable
                                accept=".xlsx, .xls"
                                onChange={handleFileUpload}
                            />
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
                        <button onClick={() => 0}>Process LinkedIn URLs</button>
                        <section className="filtered-guests-section">
                            <h2>Filtered Emails</h2>
                            <ul></ul>
                        </section>
                    </section>
                </div>
                <section className="chat-section">
                    <Chat />
                </section>
            </main>
        </div>
    );
}

export default App;
