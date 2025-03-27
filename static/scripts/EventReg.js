document.addEventListener("DOMContentLoaded", function () {
    updateEventDetails();
    autoFillUserDetails(); // New function to prefill user details
    const form = document.getElementById("registrationForm");
    if (form) {
        form.addEventListener("submit", submitForm);
    }
});
// Function to prefill user details
function autoFillUserDetails() {
    fetch('/get-user-details')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById("name").value = data.name;
                document.getElementById("email").value = data.email;
                document.getElementById("phone").value = data.phone;
            }
        })
        .catch(error => console.error("Error fetching user details:", error));
}

function updateEventDetails() {
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get("event");

    const eventNames = {
        "event1": "Konkani Mai Bhas",
        "event2": "Konkani Food & Cultural Festival 2025",
        "event3": "Konkani Heritage & Literature Meet"
    };

    const eventNameElement = document.getElementById("eventName");
    const eventInputElement = document.getElementById("eventInput");

    if (eventId && eventNameElement && eventInputElement) {
        const eventName = eventNames[eventId] || "Unknown Event";
        eventNameElement.textContent = eventName;
        eventInputElement.value = eventName;
    }
}

function updateSubsections() {
    const totalPeople = parseInt(document.getElementById("people").value);
    const subsections = document.getElementById("subsections");

    if (totalPeople >= 1) {
        subsections.style.display = "block";
        document.getElementById("adults").max = totalPeople;
        document.getElementById("children").max = totalPeople;
    } else {
        subsections.style.display = "none";
    }
}

function validatePeople() {
    const totalPeople = parseInt(document.getElementById("people").value);
    let adults = parseInt(document.getElementById("adults").value) || 0;
    let children = parseInt(document.getElementById("children").value) || 0;

    if (adults > totalPeople) {
        document.getElementById("adults").value = totalPeople;
        adults = totalPeople;
    }

    if (children > totalPeople - adults) {
        document.getElementById("children").value = totalPeople - adults;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const redirectBtn = document.getElementById("redirectBtn");
    if (redirectBtn) {
        redirectBtn.addEventListener("click", function () {
            window.location.href = "{{ url_for('home') }}";
        });
    }
});


// function submitForm(event) {
//     event.preventDefault();

//     // Validate before submission
//     validatePeople();

//     const form = document.getElementById("registrationForm");
//     const formData = new FormData(form);

//     fetch(form.action, {
//         method: "POST",
//         body: formData
//     })
//     .then(response => response.json())  // Convert response to JSON
//     .then(data => {
//         if (data.success) {
//             // Hide form and show thank you message
//             form.style.display = "none";
//             document.getElementById("thankYouMessage").style.display = "block";
//             document.getElementById("overlay").style.display = "block";

//             // Redirect after 3 seconds
//             setTimeout(() => {
//                 window.location.href = document.getElementById("thankYouMessage").getAttribute("data-home-url");
//             }, 3000);
//         } else {
//             alert(data.message);  // Show error message if registration fails
//         }
//     })
//     .catch(error => {
//         console.error("Error:", error);
//         alert("Something went wrong. Please try again later.");
//     });
// }

function submitForm(event) {
    event.preventDefault();

    // Validate before submission
    validatePeople();

    const form = document.getElementById("registrationForm");
    const formData = new FormData(form);

    fetch(form.action, {
        method: "POST",
        body: formData
    })
    .then(response => response.json())  // ✅ Convert response to JSON
    .then(data => {
        if (data.success) {
            // ✅ Show thank-you message on success
            form.style.display = "none";
            document.getElementById("thankYouMessage").style.display = "block";
            document.getElementById("overlay").style.display = "block";

            // Redirect after 3 seconds
            setTimeout(() => {
                window.location.href = document.getElementById("thankYouMessage").getAttribute("data-home-url");
            }, 3000);
        } else {
            alert(data.message);  // Show error message if registration fails
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Something went wrong. Please try again later.");
    });
}
