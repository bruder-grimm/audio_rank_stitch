// Poll for status updates
function updateStatus() {
    fetch('/api/status')
        .then(resp => resp.json())
        .then(data => {
            const instructionEl = document.getElementById('instruction');
            const bodyEl = document.body;
            
            if (data.instruction) {
                // Update instruction text while preserving the cursor
                instructionEl.innerHTML = data.instruction + '<span class="cursor"></span>';
            }
            
            if (data.background_color) {
                bodyEl.style.backgroundColor = data.background_color;
            }
            
            if (data.text_color) {
                instructionEl.style.color = data.text_color;
            }
        })
        .catch(err => console.error('Error fetching status:', err));
}

// Handle spacebar key events
document.addEventListener('keydown', function(event) {
    if (event.code === 'Space' || event.key === ' ') {
        event.preventDefault();
        fetch('/api/spacebar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: 'down' })
        })
        .catch(err => console.error('Error sending spacebar down event:', err));
    }
});

document.addEventListener('keyup', function(event) {
    if (event.code === 'Space' || event.key === ' ') {
        event.preventDefault();
        fetch('/api/spacebar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: 'up' })
        })
        .catch(err => console.error('Error sending spacebar up event:', err));
    }
});

// Ensure focus so we capture keyboard events
document.addEventListener('DOMContentLoaded', function() {
    document.body.focus();
    window.addEventListener('blur', function() {
        setTimeout(function() {
            document.body.focus();
        }, 100);
    });
});

// Initial load and periodic refresh
updateStatus();
setInterval(updateStatus, 500);
