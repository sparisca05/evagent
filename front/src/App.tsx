import { useState, useEffect } from "react";
import axios from "axios";
import { FaRegComment, FaArrowDown } from "react-icons/fa";

import Chat from "./components/Chat/Chat";
import ConnectionSetup from "./components/ConnectionSetup/ConnectionSetup";
import "./App.css";
import { FaCircleChevronRight } from "react-icons/fa6";

// Generate a unique session ID
const sessionId = `session-${Date.now()}-${Math.random().toString(36)}`;

function App() {
    const [isConnected, setIsConnected] = useState(false);
    const [activeSection, setActiveSection] = useState<
        "description" | "file" | "process" | "emails"
    >("description");
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [companyData, setCompanyData] = useState({
        name: "",
        description: "",
        idealProfile: "",
    });
    const sampleData = {
        name: "TechFlow Solutions",
        description:
            "TechFlow Solutions is a cloud consulting firm specializing in digital transformation and cloud migration services. We help enterprises modernize their infrastructure and move to the cloud securely and efficiently.\nOur main services include:\n- Cloud architecture design and implementation\n- Legacy system modernization\n- DevOps automation\n- Cloud security and compliance\n\nWe primarily work in the enterprise IT sector, focusing on medium to large businesses looking to optimize their cloud infrastructure.",
        idealProfile:
            "We're looking for:\n- IT Directors, CTOs, or Technical Project Managers\n- Decision-makers in companies with 100+ employees\n- Professionals in industries going through digital transformation\n- Companies currently using on-premises infrastructure\n- Organizations in regulated industries (finance, healthcare, etc.)\n\nPreferably in companies that have expressed interest in cloud migration or have legacy systems.",
    };
    const [descriptionLoading, setDescriptionLoading] = useState(false);
    const [descriptionResponse, setDescriptionResponse] = useState("");
    const [sendButtonDisabled, setSendButtonDisabled] = useState(false);
    const [profileData, setProfileData] = useState<
        {
            match_reason: string;
            recommendations?: string;
            email: string;
            linkedinUrl: string;
        }[]
    >([]);
    const [linkedinUrls, setLinkedinUrls] = useState<string[]>();
    const [filePlaceholder, setFilePlaceholder] = useState(
        "Drag and drop a file or click to select"
    );
    const [processing, setProcessing] = useState(false);
    const [processButtonDisabled, setProcessButtonDisabled] = useState(false);
    const [filteredData, setFilteredData] = useState<
        {
            analysis: {
                profile: { name: string };
            };
            match_reason: string;
            recommendations?: string;
            url: string;
        }[]
    >([]);
    const [emailsCreated, setEmailsCreated] = useState(false);
    const [emails, setEmails] = useState<string>();

    // Check connection status on component mount
    useEffect(() => {
        checkConnectionStatus();
    }, []);

    const checkConnectionStatus = async () => {
        try {
            const response = await axios.get(
                "http://localhost:8000/connection_status/"
            );
            if (response.data.connected) {
                setIsConnected(true);
            }
        } catch (error) {
            console.error("Error checking connection status:", error);
        }
    };

    const handleConnectionEstablished = async (connString: string) => {
        try {
            await axios.post("http://localhost:8000/set_connection/", {
                connection_string: connString,
            });
            setIsConnected(true);
        } catch (error) {
            console.error("Error setting connection:", error);
            alert("Failed to establish connection. Please try again.");
        }
    };

    const handleCompanyDataChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => {
        const { name, value } = e.target;
        setCompanyData((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    const handleCompanyDataSubmit = async (e: any) => {
        e.preventDefault();
        setSendButtonDisabled(true);
        setDescriptionLoading(true);
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
            setDescriptionResponse(response.data.response);
            setActiveSection("file"); // Avanzar a la siguiente sección
        } catch (error) {
            console.error("Error sending company data:", error);
        }
        setDescriptionLoading(false);
    };

    const handleFileUpload = async (event: any) => {
        const file = event.target.files
            ? event.target.files[0]
            : event.dataTransfer.files[0];
        if (file) {
            setFilePlaceholder(file.name);
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
                const profileData = response.data.linkedin_data;
                setProfileData(profileData);
                setLinkedinUrls(
                    profileData.map((item: any) => item.linkedinUrl)
                );
                setActiveSection("process"); // Avanzar a la siguiente sección
            } catch (error) {
                console.error("Error uploading file:", error);
            }
        }
    };

    const handleProcessLinkedinUrls = async () => {
        setProcessButtonDisabled(true);
        setProcessing(true);
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
            setFilteredData(response.data.potential_clients);
            setActiveSection("emails"); // Avanzar a la siguiente sección
        } catch (error) {
            console.error("Error processing LinkedIn URLs:", error);
        }
        setProcessing(false);
        const newProfileData = profileData.map((item) => {
            const filteredItem = filteredData.find(
                (filtered) => filtered.url === item.linkedinUrl
            );
            if (filteredItem) {
                return {
                    ...item,
                    match_reason: filteredItem.match_reason,
                    recommendations: filteredItem.recommendations,
                };
            } else {
                return {
                    ...item,
                    match_reason: "",
                    recommendations: "",
                };
            }
        });
        setProfileData(
            newProfileData.filter((item) => item.match_reason !== "")
        );

        console.log(
            "Filtered data:",
            newProfileData.filter((item) => item.match_reason !== "")
        );
    };

    const handleSendEmails = async () => {
        console.log("Creating emails...");
        try {
            // Format the data for easier processing
            const clientsInfo = filteredData.map((client) => ({
                name: client.analysis?.profile?.name || "Client",
                reason: client.match_reason || "",
                url: client.url || "",
            }));

            const response = await axios.post(
                "http://localhost:8000/chat/",
                {
                    session_id: sessionId,
                    message: `Create personalized email drafts for the following potential clients:
                    Company Information:
                    Name: ${companyData.name}
                    Description: ${companyData.description}
                    
                    Clients:
                    ${clientsInfo
                        .map(
                            (client) =>
                                `- Name: ${client.name}
                         - LinkedIn: ${client.url}
                         - Match Reason: ${client.reason}`
                        )
                        .join("\n")}
                    
                    Create a personalized email draft for each client, incorporating their specific match reasons and our company's value proposition.`,
                },
                {
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );
            setEmailsCreated(true);
            setEmails(response.data.response);
            console.log("Response from writer agent:", response.data);

            // Show the generated email drafts to the user
            if (response.data && response.data.response) {
                alert(
                    "Email drafts generated successfully! Check the response for the personalized content."
                );
            }
        } catch (error) {
            console.error("Error creating emails:", error);
        }
        /*
        console.log("Sending emails...");
        try {
            const response = await axios.post(
                "http://localhost:8000/send_emails/",
                { potential_clients: filteredEmails },
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
        */
    };

    return (
        <>
            {!isConnected ? (
                <ConnectionSetup
                    onConnectionEstablished={handleConnectionEstablished}
                />
            ) : (
                <div
                    className={`app ${
                        isChatOpen ? "chat-open" : "chat-closed"
                    }`}
                >
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
                                    Your AI-powered LinkedIn Lead Generation
                                    Assistant
                                    <br />
                                    <br />
                                    Evagent helps businesses identify and
                                    connect with their ideal clients by
                                    intelligently analyzing LinkedIn profiles.
                                    Here's how it works:
                                    <br />
                                    <br />
                                    1. Tell us about your business and ideal
                                    customer profile
                                    <br />
                                    2. Upload a list of LinkedIn profiles to
                                    analyze
                                    <br />
                                    3. Let our AI analyze and match profiles to
                                    your criteria
                                    <br />
                                    4. Generate personalized outreach emails for
                                    qualified leads
                                    <br />
                                    <br />
                                    Perfect for sales teams, recruiters, and
                                    business developers who want to:
                                    <br />
                                    • Save time on lead qualification
                                    <br />
                                    • Improve targeting accuracy
                                    <br />
                                    • Create personalized outreach at scale
                                    <br />
                                    • Connect with the right decision-makers
                                    <br />
                                </h3>
                                <a href="#steps-section" className="btn">
                                    <span className="btn-text-one">
                                        Get Started
                                    </span>
                                    <span className="btn-text-two">
                                        <FaArrowDown size={20} />
                                    </span>
                                </a>
                            </section>
                            <section
                                className="steps-section"
                                id="steps-section"
                            >
                                <section
                                    className={`step-container ${
                                        activeSection === "description"
                                            ? "active"
                                            : "inactive"
                                    }`}
                                >
                                    <h2>
                                        Step 1: Provide your company information
                                    </h2>
                                    <div className="description-section step-content">
                                        <form
                                            onSubmit={handleCompanyDataSubmit}
                                        >
                                            <div>
                                                <label>Name</label>
                                                <input
                                                    name="name"
                                                    type="text"
                                                    value={companyData.name}
                                                    onChange={
                                                        handleCompanyDataChange
                                                    }
                                                    placeholder="Enter your company name"
                                                />
                                            </div>
                                            <div>
                                                <label>
                                                    Description{" "}
                                                    <span className="info">
                                                        <span
                                                            id="profile-info"
                                                            className="info-icon"
                                                        >
                                                            i
                                                        </span>

                                                        <p
                                                            id="profile-info-text"
                                                            className="info-text"
                                                        >
                                                            A detailed
                                                            description will
                                                            help the AI
                                                            understand your
                                                            business better.
                                                        </p>
                                                    </span>
                                                </label>
                                                <textarea
                                                    name="description"
                                                    maxLength={500}
                                                    value={
                                                        companyData.description
                                                    }
                                                    onChange={
                                                        handleCompanyDataChange
                                                    }
                                                    placeholder={`Describe your company and its services or products.\n\nBe specific and ensure to include this details:\n- What does your company do?\n- What are your main products or services?\n- What is your main industry activity?`}
                                                />
                                            </div>
                                            <div>
                                                <label>
                                                    Ideal profile{" "}
                                                    <span className="info">
                                                        <span
                                                            id="profile-info"
                                                            className="info-icon"
                                                        >
                                                            i
                                                        </span>

                                                        <p
                                                            id="profile-info-text"
                                                            className="info-text"
                                                        >
                                                            A detailed
                                                            description will
                                                            help the AI filter
                                                            the LinkedIn
                                                            profiles more
                                                            effectively.
                                                        </p>
                                                    </span>
                                                </label>
                                                <textarea
                                                    name="idealProfile"
                                                    maxLength={300}
                                                    value={
                                                        companyData.idealProfile
                                                    }
                                                    onChange={
                                                        handleCompanyDataChange
                                                    }
                                                    placeholder={`Describe the ideal profile of your potential clients.\n\nBe specific and ensure to include this details:\n- What is the job title or role of your ideal client?\n- What industry or sector do they belong to?\n- Any other specific characteristics?`}
                                                />
                                            </div>
                                            <button
                                                type="button"
                                                className="btn-sample"
                                                onClick={() => {
                                                    setCompanyData(sampleData);
                                                }}
                                            >
                                                Use sample values
                                            </button>
                                            <button
                                                type="submit"
                                                disabled={sendButtonDisabled}
                                            >
                                                Submit
                                            </button>
                                        </form>
                                    </div>
                                    <div className="agent-response-section">
                                        <h2>Agent Response</h2>
                                        <p>
                                            {descriptionLoading ? (
                                                <span className="loading-text">
                                                    Loading response...
                                                </span>
                                            ) : (
                                                <span className="response-text">
                                                    {descriptionResponse}
                                                </span>
                                            )}
                                        </p>
                                    </div>
                                </section>

                                <section
                                    className={`step-container ${
                                        activeSection === "file"
                                            ? "active"
                                            : "inactive"
                                    }`}
                                >
                                    <h2>
                                        Step 2: Upload a file with invitees
                                        profiles
                                    </h2>
                                    <div className="step-content">
                                        <section className="file-upload-section">
                                            <label className="file-upload-label">
                                                <span className="file-icon">
                                                    📁
                                                </span>
                                                <input
                                                    name="file"
                                                    type="file"
                                                    draggable
                                                    accept=".xlsx, .xls"
                                                    onDrop={(e) => {
                                                        e.preventDefault();
                                                        handleFileUpload(e);
                                                    }}
                                                    onDragOver={(e) =>
                                                        e.preventDefault()
                                                    }
                                                    onChange={handleFileUpload}
                                                />
                                                <span>{filePlaceholder}</span>
                                            </label>
                                        </section>
                                    </div>
                                    <h2>Extracted LinkedIn URLs</h2>
                                    <ul>
                                        {linkedinUrls !== undefined &&
                                            linkedinUrls.map((url, index) => (
                                                <li key={index}>
                                                    <a
                                                        href={url}
                                                        target="_blank"
                                                    >
                                                        {url}
                                                    </a>
                                                </li>
                                            ))}
                                    </ul>
                                </section>

                                <section
                                    className={`step-container ${
                                        activeSection === "process"
                                            ? "active"
                                            : "inactive"
                                    }`}
                                >
                                    <h2>Step 3: Process LinkedIn URLs</h2>
                                    <div className="step-content">
                                        <button
                                            onClick={handleProcessLinkedinUrls}
                                            disabled={processButtonDisabled}
                                        >
                                            Process LinkedIn URLs
                                        </button>
                                    </div>
                                    <section className="filtered-guests-section">
                                        <h2>Filtered Users</h2>
                                        {processing ? (
                                            <span className="loading-text">
                                                Processing LinkedIn URLs...
                                            </span>
                                        ) : (
                                            <ul>
                                                {filteredData.length > 0 &&
                                                    filteredData.map(
                                                        (item, index) => (
                                                            <li key={index}>
                                                                <strong>
                                                                    Name:
                                                                </strong>{" "}
                                                                {item.url}
                                                                <br />
                                                                <strong>
                                                                    Match
                                                                    reason:
                                                                </strong>{" "}
                                                                {
                                                                    item.match_reason
                                                                }
                                                            </li>
                                                        )
                                                    )}
                                            </ul>
                                        )}
                                    </section>
                                </section>

                                <section
                                    className={`step-container ${
                                        activeSection === "emails"
                                            ? "active"
                                            : "inactive"
                                    }`}
                                >
                                    <h2>Step 4: Send Emails</h2>
                                    <div className="step-content">
                                        {emailsCreated && (
                                            <p className="success-message">
                                                Emails created successfully!
                                            </p>
                                        )}
                                        <p className="info-message">
                                            You can send personalized emails to
                                            the filtered users based on the
                                            generated drafts.
                                            <br />
                                            Click the button below to send
                                            emails.
                                        </p>
                                        <button
                                            onClick={handleSendEmails}
                                            disabled={emailsCreated}
                                        >
                                            Generate Emails
                                        </button>
                                    </div>
                                    <h2>Agent Response</h2>
                                    <section className="agent-response-section">
                                        <p>
                                            {emailsCreated && (
                                                <span className="response-text">
                                                    {emails}
                                                </span>
                                            )}
                                        </p>
                                    </section>
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
                                            <FaRegComment
                                                size={34}
                                                color="#577397"
                                            />
                                        </span>
                                        <p>Agent chat</p>
                                        <span className="demo">demo</span>
                                    </div>
                                )}
                            </div>
                            <Chat
                                sessionId={sessionId}
                                isVisible={isChatOpen}
                            />
                        </section>
                    </main>
                </div>
            )}
        </>
    );
}

export default App;
