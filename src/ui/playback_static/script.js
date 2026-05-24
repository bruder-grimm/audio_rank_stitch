// Update slider values display
const sliders = {
    attack: document.getElementById('attack'),
    decay: document.getElementById('decay'),
    silence: document.getElementById('silence'),
    shuffle: document.getElementById('shuffle'),
    topk: document.getElementById('topk'),
};

const valueDisplays = {
    attack: document.getElementById('attack-value'),
    decay: document.getElementById('decay-value'),
    silence: document.getElementById('silence-value'),
    shuffle: document.getElementById('shuffle-value'),
    topk: document.getElementById('topk-value'),
};

// Update displays and send to server
Object.entries(sliders).forEach(([key, slider]) => {
    slider.addEventListener('input', (e) => {
        const value = e.target.value;
        if (key === 'silence') {
            valueDisplays[key].textContent = parseFloat(value).toFixed(1);
        } else {
            valueDisplays[key].textContent = value;
        }
        
        // Send update to server
        const payload = {};
        switch (key) {
            case 'attack':
                payload.attack = parseInt(value);
                break;
            case 'decay':
                payload.decay = parseInt(value);
                break;
            case 'silence':
                payload.silence_duration = parseFloat(value);
                break;
            case 'shuffle':
                payload.shuffle_factor = parseInt(value);
                break;
            case 'topk':
                payload.top_k = parseInt(value);
                break;
        }
        
        fetch('/api/state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).catch(err => console.error('Error updating state:', err));
    });
});

// Play button
document.getElementById('play-btn').addEventListener('click', () => {
    fetch('/api/play', { method: 'POST' })
        .catch(err => console.error('Error triggering play:', err));
});

// Poll for words updates
function updateWords() {
    fetch('/api/words')
        .then(resp => resp.json())
        .then(data => {
            const wordsList = document.getElementById('words-list');
            if (data.words && data.words.length > 0) {
                wordsList.innerHTML = data.words
                    .map(w => `<li>${w.word}: ${w.count}</li>`)
                    .join('');
            } else {
                wordsList.innerHTML = '<li class="placeholder">No words loaded yet...</li>';
            }
        })
        .catch(err => console.error('Error fetching words:', err));
}

// Initial load and periodic refresh
updateWords();
setInterval(updateWords, 1000);

// ===== POLLING FOR SETTINGS UPDATES FROM OTHER CLIENTS =====
// This allows multiple users to see each other's slider changes in real-time
// Only updates UI if: (1) value changed AND (2) user is not currently dragging

let lastKnownSettings = {};

function pollSettingsFromServer() {
    fetch('/api/state')
        .then(resp => resp.json())
        .then(remoteSettings => {
            // Map API keys to UI element IDs
            const keyMapping = {
                'attack': 'attack',
                'decay': 'decay',
                'silence_duration': 'silence',
                'shuffle_factor': 'shuffle',
                'top_k': 'topk',
            };
            
            Object.entries(keyMapping).forEach(([apiKey, uiKey]) => {
                const remoteValue = remoteSettings[apiKey];
                const slider = sliders[uiKey];
                const display = valueDisplays[uiKey];
                
                if (!slider || remoteValue === undefined) return;
                
                // Only update if:
                // 1. Value actually changed from last poll
                // 2. User is NOT currently focused/dragging this slider
                if (lastKnownSettings[apiKey] !== remoteValue && 
                    document.activeElement !== slider) {
                    
                    slider.value = remoteValue;
                    
                    // Update display
                    if (uiKey === 'silence') {
                        display.textContent = parseFloat(remoteValue).toFixed(1);
                    } else {
                        display.textContent = Math.round(remoteValue);
                    }
                    
                    lastKnownSettings[apiKey] = remoteValue;
                }
            });
        })
        .catch(err => console.error('Error polling settings:', err));
}

// Poll every 2 seconds for settings changes from other clients
// This keeps the UI in sync across multiple browser tabs/windows
setInterval(pollSettingsFromServer, 2000);

// Initial poll to sync on page load
pollSettingsFromServer();
