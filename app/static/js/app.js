// Global state
let activeAgent = null;
let currentModels = {};
let availableModels = [];
let selectedCollections = [];
let client_id = null; // New global variable for client ID
let websocket = null; // New global variable for WebSocket connection

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    client_id = crypto.randomUUID(); // Generate a unique client ID
    await checkConnections();
    await loadSettings();
    setupEventListeners();
    connectWebSocket(); // Establish WebSocket connection
});

// Event Listeners
function setupEventListeners() {
    // Execute button
    document.getElementById('executeBtn').addEventListener('click', executeAgents);
    document.getElementById('queryInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeAgents();
    });
    
    // Modal buttons
    document.getElementById('settingsBtn').addEventListener('click', () => openModal('settingsModal'));
    document.getElementById('historyBtn').addEventListener('click', () => {
        openModal('historyModal');
        loadHistory();
    });
    document.getElementById('promptsBtn').addEventListener('click', () => {
        openModal('promptsModal');
        loadPrompts();
    });
    
    // Close buttons
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(btn.closest('.modal').id);
        });
    });
    
    // Upload button
    document.getElementById('uploadBtn').addEventListener('click', () => {
        document.getElementById('fileInput').click();
    });
    
    // Upload button in main input
    document.getElementById('mainUploadBtn').addEventListener('click', () => {
        document.getElementById('mainFileInput').click();
    });
    
    document.getElementById('mainFileInput').addEventListener('change', displayMainSelectedFiles);
}

// Function to establish WebSocket connection
function connectWebSocket() {
    const ws_protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const ws_url = `${ws_protocol}${window.location.host}/ws/${client_id}`;
    websocket = new WebSocket(ws_url);

    websocket.onopen = (event) => {
        addLog('System', `WebSocket connected for client ${client_id}.`, false);
    };

    websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.task_id) {
            addLog('System', `Received update for task ${message.task_id}. Status: ${message.status}`, false);
            if (message.status === 'SUCCESS') {
                const result = message.result;
                displayExecutionPlan(result.plan);
                document.getElementById('results').innerHTML = `<pre>${result.final_result}</pre>`;
                addLog('Master Agent', `Execution completed in ${result.duration ? result.duration.toFixed(2) : 'N/A'}s`, false);
                setLoading(false); // Task completed, stop loading
            } else if (message.status === 'FAILURE') {
                addLog('System', `Task ${message.task_id} failed: ${message.error}`, true);
                setLoading(false); // Task failed, stop loading
            }
        }
    };

    websocket.onclose = (event) => {
        addLog('System', `WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`, true);
        // Attempt to reconnect after a delay
        setTimeout(connectWebSocket, 5000);
    };

    websocket.onerror = (error) => {
        addLog('System', `WebSocket error: ${error.message}`, true);
        websocket.close();
    };
}

// Helper to display selected files in the main input section
function displayMainSelectedFiles() {
    const fileInput = document.getElementById('mainFileInput');
    const displayDiv = document.getElementById('selectedFilesDisplay');
    displayDiv.innerHTML = ''; // Clear previous selections
    
    if (fileInput.files.length > 0) {
        const ul = document.createElement('ul');
        for (let i = 0; i < fileInput.files.length; i++) {
            const li = document.createElement('li');
            li.textContent = fileInput.files[i].name;
            ul.appendChild(li);
        }
        displayDiv.appendChild(ul);
    }
}

// Regex to extract URLs
function extractUrls(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.match(urlRegex) || [];
}

// API Calls
async function executeAgents() {
    const queryInput = document.getElementById('queryInput');
    let query = queryInput.value.trim();
    
    const mainFileInput = document.getElementById('mainFileInput');
    const files = mainFileInput.files;
    
    const urls = extractUrls(query);
    
    // Remove URLs from the query text
    urls.forEach(url => {
        query = query.replace(url, '').trim();
    });

    if (!query && files.length === 0 && urls.length === 0) {
        alert('Please enter a query, upload files, or include URLs.');
        return;
    }
    
    setLoading(true);
    clearResults();
    
    const formData = new FormData();
    formData.append('query', query);
    formData.append('collections_str', JSON.stringify(selectedCollections));
    formData.append('urls_str', JSON.stringify(urls));
    formData.append('client_id', client_id); // Add client_id to form data

    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        const response = await fetch('/api/agents/execute', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        addLog('System', `Task ${data.task_id} accepted. Waiting for results...`, false);
        
        // Clear inputs after task accepted
        queryInput.value = '';
        mainFileInput.value = '';
        displayMainSelectedFiles(); // Clear displayed files
        
    } catch (error) {
        addLog('System', `Error: ${error.message}`, true);
        setLoading(false); // Stop loading on immediate error
    }
}

async function checkConnections() {
    try {
        const response = await fetch('/api/settings/connections');
        const status = await response.json();
        
        const banner = document.getElementById('connectionBanner');
        const text = document.getElementById('connectionText');
        
        const disconnected = Object.entries(status)
            .filter(([key, value]) => !value)
            .map(([key]) => key);
        
        if (disconnected.length > 0) {
            text.textContent = `Services not connected: ${disconnected.join(', ')}`;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
        
        return status;
    } catch (error) {
        console.error('Connection check failed:', error);
        return { ollama: false, qdrant: false, redis: false };
    }
}

async function loadSettings() {
    try {
        // Load models
        const modelsRes = await fetch('/api/settings/models');
        const modelsData = await modelsRes.json();
        availableModels = modelsData.models;
        
        // Load current agent models
        const agentModelsRes = await fetch('/api/settings/agent-models');
        currentModels = await agentModelsRes.json();
        
        // Load collections
        const collectionsRes = await fetch('/api/collections/');
        const collectionsData = await collectionsRes.json();
        
        // Load selected collections
        const selectedRes = await fetch('/api/settings/selected-collections');
        const selectedData = await selectedRes.json();
        selectedCollections = selectedData.collections;
        
        // Update UI
        updateSettingsUI(collectionsData.collections);
        
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history/');
        const data = await response.json();
        
        const historyList = document.getElementById('historyList');
        
        if (data.history.length === 0) {
            historyList.innerHTML = '<p class="empty-state">No conversation history yet</p>';
            return;
        }
        
        historyList.innerHTML = data.history.map(session => `
            <div class="history-item ${session.status}">
                <div class="history-header">
                    <span class="history-status ${session.status}">
                        ${session.status === 'success' ? '✓ SUCCESS' : '✗ FAILED'}
                    </span>
                    <span class="history-time">${new Date(session.timestamp).toLocaleString()}</span>
                </div>
                <div class="history-query">${session.input.substring(0, 100)}${session.input.length > 100 ? '...' : ''}</div>
                <div class="history-meta">
                    Duration: ${session.duration?.toFixed(2)}s | Model: ${session.model || 'unknown'}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

async function loadPrompts() {
    try {
        const response = await fetch('/api/settings/system-prompts');
        const prompts = await response.json();
        
        const promptsList = document.getElementById('promptsList');
        
        promptsList.innerHTML = Object.entries(prompts).map(([key, prompt]) => `
            <div class="prompt-editor">
                <div class="prompt-header">
                    <h3>${prompt.name}</h3>
                    <div class="btn-group">
                        <button class="btn-secondary btn-small" onclick="savePrompt('${key}')">Save</button>
                    </div>
                </div>
                <textarea id="prompt-${key}" rows="6">${prompt.current}</textarea>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load prompts:', error);
    }
}

async function savePrompt(agent) {
    const textarea = document.getElementById(`prompt-${agent}`);
    const prompt = textarea.value;
    
    try {
        await fetch('/api/settings/system-prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent, prompt })
        });
        
        alert('Prompt saved successfully!');
    } catch (error) {
        alert('Failed to save prompt: ' + error.message);
    }
}

async function uploadDocuments() {
    const fileInput = document.getElementById('fileInput');
    const files = fileInput.files;
    
    if (files.length === 0 || selectedCollections.length === 0) {
        alert('Please select files and a collection');
        return;
    }
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    formData.append('collection', selectedCollections[0]);
    
    try {
        const response = await fetch('/api/collections/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }

        const data = await response.json();
        alert(`Uploaded ${data.results.length} files successfully!`);
        fileInput.value = '';
    } catch (error) {
        alert('Upload failed: ' + error.message);
    }
}

// UI Helpers
function updateSettingsUI(collections) {
    // Connection status
    const statusHtml = `
        <div class="status-item">
            <span class="status-icon">⚙️</span>
            <span>Ollama</span>
        </div>
        <div class="status-item">
            <span class="status-icon">🗄️</span>
            <span>Qdrant</span>
        </div>
        <div class="status-item">
            <span class="status-icon">⚡</span>
            <span>Redis</span>
        </div>
    `;
    document.getElementById('connectionStatus').innerHTML = statusHtml;
    
    // Model settings
    const modelHtml = ['master', 'ocr', 'info', 'rag', 'embedding'].map(agent => `
        <div class="model-select">
            <label>${agent.toUpperCase()} Agent Model:</label>
            <select id="model-${agent}" onchange="updateModel('${agent}', this.value)">
                ${availableModels.map(m => `
                    <option value="${m.name}" ${currentModels[agent] === m.name ? 'selected' : ''}>
                        ${m.name}
                    </option>
                `).join('')}
            </select>
        </div>
    `).join('');
    document.getElementById('modelSettings').innerHTML = modelHtml;
    
    // Collection settings
    const collectionHtml = `
        <div class="checkbox-group">
            ${collections.map(c => `
                <label class="checkbox-item">
                    <input type="checkbox" 
                           value="${c.name}" 
                           ${selectedCollections.includes(c.name) ? 'checked' : ''}
                           onchange="toggleCollection('${c.name}', this.checked)">
                    <span>${c.name}</span>
                </label>
            `).join('')}
        </div>
    `;
    document.getElementById('collectionSettings').innerHTML = collectionHtml;
}

async function updateModel(agent, model) {
    currentModels[agent] = model;
    
    try {
        await fetch('/api/settings/agent-models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentModels)
        });
    } catch (error) {
        console.error('Failed to update model:', error);
    }
}

async function toggleCollection(collection, checked) {
    if (checked) {
        selectedCollections.push(collection);
    } else {
        selectedCollections = selectedCollections.filter(c => c !== collection);
    }
    
    try {
        await fetch('/api/settings/selected-collections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collections: selectedCollections })
        });
    } catch (error) {
        console.error('Failed to update collections:', error);
    }
}

function displayExecutionPlan(plan) {
    const executionPlanDiv = document.getElementById('executionPlan');
    if (!plan) {
        executionPlanDiv.innerHTML = '<p class="empty-state">Execution plan not available.</p>';
        return;
    }
    const planHtml = `
        <div style="margin-bottom: 1rem;">
            <strong>Agents:</strong> ${plan.agents.join(', ')}
        </div>
        <div style="margin-bottom: 1rem;">
            <strong>Mode:</strong> ${plan.execution_mode}
        </div>
        <div>
            <strong>Steps:</strong>
            ${plan.steps.map(step => `
                <div style="padding: 0.5rem; margin: 0.5rem 0; background: #0f172a; border-radius: 0.375rem;">
                    <strong>${step.id}. ${step.agent}</strong><br>
                    <span style="color: #94a3b8; font-size: 0.875rem;">${step.action}</span>
                </div>
            `).join('')}
        </div>
    `;
    executionPlanDiv.innerHTML = planHtml;
}

function addLog(agent, message, isError = false) {
    const logsDiv = document.getElementById('activityLogs');
    
    if (logsDiv.querySelector('.empty-state')) {
        logsDiv.innerHTML = '';
    }
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${isError ? 'error' : ''}`;
    logEntry.innerHTML = `
        <div class="log-header">
            <span class="log-agent">${agent}</span>
            <span class="log-time">${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="log-message">${message}</div>
    `;
    
    logsDiv.insertBefore(logEntry, logsDiv.firstChild);
    
    // Highlight active agent
    setActiveAgent(agent);
}

function setActiveAgent(agentName) {
    document.querySelectorAll('.agent-card').forEach(card => {
        if (card.querySelector('h3').textContent === agentName) {
            card.classList.add('active');
            setTimeout(() => card.classList.remove('active'), 2000);
        }
    });
}

function clearResults() {
    document.getElementById('executionPlan').innerHTML = '<p class="empty-state">Plan will appear here</p>';
    document.getElementById('activityLogs').innerHTML = '<p class="empty-state">No activity yet</p>';
}

function setLoading(loading) {
    const btn = document.getElementById('executeBtn');
    const text = document.getElementById('executeText');
    const spinner = document.getElementById('loadingSpinner');
    
    btn.disabled = loading;
    text.classList.toggle('hidden', loading);
    spinner.classList.toggle('hidden', !loading);
}

function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

// Close modal on outside click
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal(modal.id);
        }
    });
});
