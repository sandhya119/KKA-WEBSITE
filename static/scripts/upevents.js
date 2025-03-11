window.onload = function() {
    checkEventExpiry();
};

// Function to check if event registration is expired
function checkEventExpiry() {
    const events = document.querySelectorAll(".event");
    const currentDate = new Date();

    events.forEach(event => {
        const eventDate = new Date(event.querySelector(".event-date").textContent.replace('Event Date: ', ''));
        const registerByDate = new Date(event.querySelector(".register-by-date").textContent.replace('Register By: ', ''));

        if (currentDate > registerByDate) {
            event.querySelector(".register-btn").style.display = "none"; 
            event.querySelector(".expired-msg").style.display = "inline"; 
        } else {
            event.querySelector(".register-btn").style.display = "inline"; 
            event.querySelector(".expired-msg").style.display = "none"; 
        }
    });
}

// Function to redirect to the registration page
function redirectToRegistration(eventId) {
    window.location.href = `EventReg.html?event=${eventId}`;
}

// Function to search through events
function searchEvents() {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let events = document.querySelectorAll(".event");
    let noResultsMessage = document.getElementById('noResults');
    let eventList = document.getElementById("eventList");
    
    let found = false;

    events.forEach(event => {
        let text = event.textContent.toLowerCase();
        if (text.includes(input)) {
            event.style.display = "flex";
            found = true;
        } else {
            event.style.display = "none";
        }
    });

    // Show "No events found" message if necessary
    if (!found) {
        if (!noResultsMessage) {
            noResultsMessage = document.createElement('p');
            noResultsMessage.id = 'noResults';
            noResultsMessage.textContent = "No events found.";
            noResultsMessage.style.textAlign = "center";
            noResultsMessage.style.fontSize = "18px";
            noResultsMessage.style.color = "gray";
            eventList.appendChild(noResultsMessage);
        }
    } else if (noResultsMessage) {
        noResultsMessage.remove();
    }
}

// Function to open modal and display image
function openModal(src) {
    document.getElementById("imageModal").style.display = "block";
    document.getElementById("modalImg").src = src;
}

// Function to close the modal
function closeModal() {
    document.getElementById("imageModal").style.display = "none";
}

// Get event ID from URL to display event name
const urlParams = new URLSearchParams(window.location.search);
const eventId = urlParams.get("event");

const eventNames = {
    "event1": "Konkani Food & Cultural Festival 2025",
    "event2": "Konkani Music & Dance Night",
    "event3": "Konkani Heritage & Literature Meet"
};

// Display the event name based on event ID
if (eventId && document.getElementById("eventName")) {
    document.getElementById("eventName").textContent = eventNames[eventId] || "Unknown Event";
}
