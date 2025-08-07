import React, { useState } from 'react';
import axios from 'axios';
import { Button, CircularProgress, TextField, Box } from '@mui/material'; // Import TextField and Box

const HubspotIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [loadedItems, setLoadedItems] = useState(''); // New state for loaded data

    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/authorize`, formData);
            const authURL = response?.data;

            const newWindow = window.open(authURL, 'HubSpot Authorization', 'width=600, height=600');

            // Polling for the window to close
            const pollTimer = window.setInterval(() => {
                if (newWindow?.closed !== false) { 
                    window.clearInterval(pollTimer);
                    handleWindowClosed();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail);
        }
    }

    const handleWindowClosed = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/credentials`, formData);
            const credentials = response.data; 
            if (credentials) {
                setIsConnecting(false);
                setIsConnected(true);
                setIntegrationParams(prev => ({ ...prev, hubspot: { credentials: credentials, type: 'HubSpot' } })); // Ensure hubspot key is used
            }
            setIsConnecting(false);
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail);
        }
    }

    const handleLoadItems = async () => {
        try {
            const formData = new FormData();
            // Access credentials from the integrationParams prop
            const credentials = integrationParams?.hubspot?.credentials;

            if (!credentials) {
                console.error('HubSpot credentials not found. Please connect first.');
                alert('HubSpot credentials not found. Please connect first.');
                return;
            }
            
            formData.append('credentials', JSON.stringify(credentials));
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/load`, formData);
            // Convert the array of objects to a pretty-printed JSON string
            setLoadedItems(JSON.stringify(response.data, null, 2)); 
        } catch (e) {
            console.error('Error loading HubSpot items:', e);
            alert(e?.response?.data?.detail || 'Error loading HubSpot items.');
        }
    };

    const handleClearItems = () => {
        setLoadedItems(''); // Clear the loaded data
    };

    // Add useEffect to check connection status on component mount or integrationParams change
    React.useEffect(() => {
        if (integrationParams?.hubspot?.credentials) {
            setIsConnected(true);
        } else {
            setIsConnected(false);
        }
    }, [integrationParams]);

    return (
        <Box sx={{ mt: 2 }}>
            <h3>HubSpot Integration</h3>
            {!isConnected ? (
                <Button 
                    variant="contained" 
                    color="primary" 
                    onClick={handleConnectClick} 
                    disabled={isConnecting}
                >
                    {isConnecting ? <CircularProgress size={24} /> : 'Connect to HubSpot'}
                </Button>
            ) : (
                <div>
                    <p>HubSpot Connected!</p>
                    <Button 
                        variant="contained" 
                        color="secondary" 
                        onClick={handleLoadItems}
                        sx={{ mr: 1 }} // Add some margin
                    >
                        Load HubSpot Items
                    </Button>
                    <Button 
                        variant="outlined" 
                        color="secondary" 
                        onClick={handleClearItems}
                    >
                        Clear Data
                    </Button>
                    <TextField
                        label="Loaded Data"
                        multiline
                        rows={10} // Adjust rows as needed
                        fullWidth
                        value={loadedItems}
                        InputProps={{
                            readOnly: true,
                        }}
                        sx={{ mt: 2 }}
                    />
                </div>
            )}
        </Box>
    );
};

export default HubspotIntegration;