import { useState } from "react";
import axios from "axios";
import { FaRegComment, FaArrowDown } from "react-icons/fa";

import Chat from "./components/Chat/Chat";
import "./App.css";
import { FaCircleChevronRight } from "react-icons/fa6";

// Generate a unique session ID
const sessionId = `session-${Date.now()}-${Math.random().toString(36)}`;

function App() {
    const [linkedinUrls, setLinkedinUrls] = useState<string[]>();
    const [filePlaceholder, setFilePlaceholder] = useState(
        "Drag and drop a file or click to select"
    );
    const [filteredData, setFilteredData] = useState<
        { email: string; linkedinUrl: string }[]
    >([]);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [companyData, setCompanyData] = useState({
        name: "",
        description: "",
        idealProfile: "",
    });

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

    const handleCompanyDataChange = (
        e: React.ChangeEvent<HTMLInputElement>
    ) => {
        const { name, value } = e.target;
        setCompanyData((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    const handleCompanyDataSubmit = async (e: any) => {
        e.preventDefault();
        try {
            const response = await axios.post(
                "http://localhost:8000/chat/",
                {
                    session_id: sessionId,
                    message: `Company Name: ${companyData.name}, Description: ${companyData.description}, Ideal Profile: ${companyData.idealProfile}`,
                },
                {
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );
            console.log("Response from agent:", response);
        } catch (error) {
            console.error("Error sending company data:", error);
        }
    };

    const handleProcessLinkedinUrls = async () => {
        console.log("Processing LinkedIn URLs...");
        try {
            const response = await axios.post(
                "http://localhost:8000/process_invitees/",
                {
                    session_id: sessionId,
                    linkedin_urls: linkedinUrls,
                },
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

    const handleSendEmails = async () => {
        console.log("Sending emails...");
        const emails = filteredData.map((item) => item.email);
        try {
            const response = await axios.post(
                "http://localhost:8000/send_emails/",
                { potential_clients: emails },
                {
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );
            console.log("Response from agent:", response.data);
            alert("Emails sent successfully!");
        } catch (error) {
            console.error("Error sending emails:", error);
        }
    };

    return (
        <div className={`app ${isChatOpen ? "chat-open" : "chat-closed"}`}>
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
                <section className="agent-section">
                    <section className="intro-section">
                        <h1>Welcome to Evagent</h1>
                        <h3>
                            <br />
                            This AI Agent helps you find potential clients for
                            your business by analyzing LinkedIn profiles.
                            <br />
                            Simply upload a file with invitee profiles, process
                            the data, and let Eva, your AI agent, assist you in
                            finding the right connections.
                            <br />
                            Finally, you can send emails to the filtered users
                            directly from this platform.
                            <br />
                        </h3>
                        <a href="#steps-section" className="btn">
                            <span className="btn-text-one">Get Started</span>
                            <span className="btn-text-two">
                                <FaArrowDown size={20} />
                            </span>
                        </a>
                    </section>
                    <section className="steps-section" id="steps-section">
                        <section className="file-section">
                            <h2>Provide your company description</h2>
                            <form
                                className="description-section"
                                onSubmit={handleCompanyDataSubmit}
                            >
                                <div>
                                    <label>Name</label>
                                    <input
                                        name="name"
                                        type="text"
                                        value={companyData.name}
                                        onChange={handleCompanyDataChange}
                                        placeholder="Enter company name"
                                    />
                                </div>
                                <div>
                                    <label>Description</label>
                                    <input
                                        name="description"
                                        type="text"
                                        value={companyData.description}
                                        onChange={handleCompanyDataChange}
                                        placeholder="Describe your company"
                                    />
                                </div>
                                <div>
                                    <label>Ideal profile</label>
                                    <input
                                        name="idealProfile"
                                        type="text"
                                        value={companyData.idealProfile}
                                        onChange={handleCompanyDataChange}
                                        placeholder="Describe your ideal customer profile"
                                    />
                                </div>
                                <button type="submit">Send</button>
                            </form>
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
                                <h2>Filtered Users</h2>
                                <ul>
                                    {filteredData.length > 0 ? (
                                        filteredData.map((item, index) => (
                                            <li key={index}>
                                                <strong>Email:</strong>{" "}
                                                {item.email}
                                                <br />
                                                <strong>
                                                    LinkedIn URL:
                                                </strong>{" "}
                                                <a
                                                    href={item.linkedinUrl}
                                                    target="_blank"
                                                >
                                                    {item.linkedinUrl}
                                                </a>
                                            </li>
                                        ))
                                    ) : (
                                        <li>No filtered URLs found.</li>
                                    )}
                                </ul>
                            </section>
                            <button onClick={handleSendEmails}>
                                Send Emails
                            </button>
                        </section>
                    </section>
                </section>
                <section
                    className={`chat-section ${
                        isChatOpen ? "expanded" : "collapsed"
                    }`}
                >
                    <div
                        className="chat-toggle"
                        onClick={() => setIsChatOpen(!isChatOpen)}
                    >
                        {isChatOpen ? (
                            <span className="chat-icon">
                                <FaCircleChevronRight
                                    size={34}
                                    color="#577397"
                                />
                            </span>
                        ) : (
                            <div>
                                <span className="chat-icon">
                                    <FaRegComment size={34} color="#577397" />
                                </span>
                                <p>Agent chat</p>
                                <span className="demo">demo</span>
                            </div>
                        )}
                    </div>
                    <Chat sessionId={sessionId} isVisible={isChatOpen} />
                </section>
            </main>
        </div>
    );
}

export default App;
