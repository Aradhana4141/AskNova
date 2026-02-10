const API_URL = "http://127.0.0.1:8000";
let currentDocID = null;
const chatBox = document.getElementById("chatBox");

// 1. Upload PDF 
document.getElementById("fileInput").addEventListener('change', handleFileSelect);

function handleFileSelect(event) {
    const file = event.target.files[0];
    
    if (!file) {
        alert("Select the file first");
        return;
    }
    
    if (!file.name.endsWith('.pdf')) {
        showStatus('error', 'Please select a PDF file');
        return;
    }

    // Show file info
    const fileInfo = document.getElementById("fileInfo");
    fileInfo.style.display = 'block';
    fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;

    uploadPDF(file);
}

// Upload PDF to backend
async function uploadPDF(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        showStatus('info', 'Uploading and processing PDF...');
        
        const response = await fetch(`${API_URL}/upload_pdf`, {
            method: 'POST',
            body: formData
        });

        console.log(response)

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("UPLOAD RESPONSE:", data);
        
        // Save doc_id
        currentDocID = data.doc_id;
        
        // Hide upload section, show chat
        document.getElementById("uploadSection").style.display = "none";
        document.getElementById("chatSection").style.display = "block";
        
        // Clear chat and show ready message
        chatBox.innerHTML = '';
        addBot(`✅ PDF processed successfully! Found ${data.nums_chunks} chunks. Ask me anything about this document.`);
        
        showStatus('success', 'PDF ready for questions!');
        
    } catch (error) {
        console.error("Upload error:", error);
        showStatus('error', `Upload failed: ${error.message}`);
    }
}

// 2. Ask Question
async function askQuestion() {
    const questionInput = document.getElementById("questionInput");
    let question = questionInput.value.trim();
    
    if (!question) {
        alert("Please enter a question");
        return;
    }
    
    if (!currentDocID) {
        alert("Upload PDF first");
        return;
    }
    
    try {
        // Show user's question
        addUser(question);
        
        // Clear input
        questionInput.value = '';
        
        // Show thinking message
        addBot("Thinking...");
        
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doc_id: currentDocID,
                question: question
            })
        });

        if (!response.ok) {
            throw new Error(`Query failed: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("QUERY RESPONSE:", data);
        
        // Remove "Thinking..." message
        chatBox.removeChild(chatBox.lastChild);
        
        // Add bot's answer
        addBot(data.answer);
        
    } catch (error) {
        console.error("Query error:", error);
        // Remove "Thinking..." if it exists
        if (chatBox.lastChild && chatBox.lastChild.textContent === "Thinking...") {
            chatBox.removeChild(chatBox.lastChild);
        }
        addBot(`❌ Error: ${error.message}`);
    }
}

// 3. Message helpers
function addUser(text) {
    let div = document.createElement("div");
    div.className = "message user";
    div.innerText = text;
    chatBox.appendChild(div);
    scroll();
}

function addBot(text) {
    let div = document.createElement("div");
    div.className = "message assistant";
    div.innerText = text;
    chatBox.appendChild(div);
    scroll();
}

function scroll() {
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showStatus(type, message) {
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.className = `status ${type}`;
    statusDiv.textContent = message;
    statusDiv.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 3000);
    }
}

function resetApp() {
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('chatSection').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('chatBox').innerHTML = '';
    document.getElementById('questionInput').value = '';
    currentDocID = null;
}