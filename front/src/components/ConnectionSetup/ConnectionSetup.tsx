import { useState } from "react";
import { FaKey, FaCheckCircle, FaExclamationTriangle } from "react-icons/fa";
import "./ConnectionSetup.css";

interface ConnectionSetupProps {
    onConnectionEstablished: (connectionString: string) => void;
}

const ConnectionSetup = ({ onConnectionEstablished }: ConnectionSetupProps) => {
    const [connectionString, setConnectionString] = useState("");
    const [isConnecting, setIsConnecting] = useState(false);
    const [error, setError] = useState("");

    const testConnection = async (connString: string): Promise<boolean> => {
        try {
            const response = await fetch(
                "http://localhost:8000/test_connection",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        connection_string: connString,
                    }),
                }
            );

            return response.ok;
        } catch (error) {
            console.error("Connection test failed:", error);
            return false;
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!connectionString.trim()) {
            setError("Please enter a connection string");
            return;
        }

        setIsConnecting(true);
        setError("");

        try {
            const isValid = await testConnection(connectionString);

            if (isValid) {
                onConnectionEstablished(connectionString);
            } else {
                setError(
                    "Invalid connection string. Please check your Azure credentials."
                );
            }
        } catch (error) {
            setError("Failed to test connection. Please try again.");
        } finally {
            setIsConnecting(false);
        }
    };

    const useSampleConnection = () => {
        const sampleConnection =
            "eastus2.api.azureml.ms;6eea0696-55fd-406f-bf32-f35b23ee1adf;rg-simonparisca-4425_ai;simonparisca-5173";
        setConnectionString(sampleConnection);
    };

    return (
        <div className="connection-setup">
            <div className="connection-setup-container">
                <div className="connection-header">
                    <div className="connection-icon">
                        <FaKey size={48} color="#577397" />
                    </div>
                    <h1>Azure Connection Setup</h1>
                    <p>
                        Please provide your Azure AI project connection string
                        to get started. This allows Evagent to connect to your
                        Azure AI services.
                    </p>
                    <p>
                        Here is a full explanation and demo video of the Agent:{" "}
                        <a
                            href="https://www.youtube.com/watch?v=XOA_AHzApTI"
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "#577397" }}
                        >
                            Watch here
                        </a>
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="connection-form">
                    <div className="form-group">
                        <label htmlFor="connectionString">
                            Azure Project Connection String
                            <span className="required">*</span>
                        </label>
                        <textarea
                            id="connectionString"
                            value={connectionString}
                            onChange={(e) =>
                                setConnectionString(e.target.value)
                            }
                            placeholder="Enter your Azure AI project connection string&#10;&#10;Format: endpoint;subscription-id;resource-group;workspace"
                            rows={4}
                            required
                        />
                        <small className="form-help">
                            You can find this in your{" "}
                            <a
                                href="https://ai.azure.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ color: "#577397" }}
                            >
                                Azure AI Studio
                            </a>{" "}
                            project settings under "Connection strings"
                        </small>
                    </div>

                    {error && (
                        <div className="error-message">
                            <FaExclamationTriangle size={16} />
                            <span>{error}</span>
                        </div>
                    )}

                    <div className="form-actions">
                        <button
                            type="button"
                            className="btn-sample"
                            onClick={useSampleConnection}
                        >
                            Use Sample Connection
                        </button>
                        <button
                            type="submit"
                            className="btn-connect"
                            disabled={isConnecting}
                        >
                            {isConnecting ? (
                                <>
                                    <span className="spinner"></span>
                                    Testing Connection...
                                </>
                            ) : (
                                <>
                                    <FaCheckCircle size={16} />
                                    Connect
                                </>
                            )}
                        </button>
                    </div>
                </form>

                <div className="connection-info">
                    <h3>Why do I need this?</h3>
                    <ul>
                        <li>Securely connects to your Azure AI services</li>
                        <li>Enables AI-powered LinkedIn profile analysis</li>
                        <li>Allows personalized email generation</li>
                        <li>
                            Your credentials never leave your browser session
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default ConnectionSetup;
