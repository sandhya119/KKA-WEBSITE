document.addEventListener("DOMContentLoaded", function() {
    const popup = document.getElementById("popup");

    // Show Popup when "Join Our Family" is clicked
    document.getElementById("joinBtn")?.addEventListener("click", function() {
        popup.style.display = "flex"; // Show the popup
    });

    // Navigate to Register Page when "Yes" is clicked
    document.getElementById("yesBtn")?.addEventListener("click", function() {
        window.location.href = "login.html"; // Redirect to Register Page
    });

    // Navigate to Login Page when "No" is clicked
    document.getElementById("noBtn")?.addEventListener("click", function() {
        window.location.href = "JoinFamReg.html"; // Redirect to Login Page
    });

    // Handle Family Form Submission
    document.getElementById("familyForm")?.addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent default submission

        let name = document.getElementById("name")?.value;
        let email = document.getElementById("email")?.value;
        let phone = document.getElementById("phone")?.value;
        let familyDetails = document.getElementById("family_details")?.value;
        let childrenCount = document.getElementById("children_count")?.value;
        let interests = document.getElementById("interests")?.value;

        let city = document.querySelector('input[name="city"]:checked');
        if (!city) {
            alert("Please select a nearest capital city.");
            return;
        }

        // Collect Family Members
        let familyMembers = [];
        document.querySelectorAll(".member-entry").forEach(member => {
            let memberName = member.querySelector("input[name='member_name[]']")?.value;
            let memberYOB = member.querySelector("input[name='member_age[]']")?.value;
            if (memberName && memberYOB) {
                familyMembers.push({ name: memberName, yearOfBirth: memberYOB });
            }
        });

        let formData = {
            name: name,
            email: email,
            city: city.value,
            phone: phone,
            familyDetails: familyDetails,
            childrenCount: childrenCount,
            interests: interests,
            familyMembers: familyMembers
        };

        console.log("Form Submitted Successfully!", formData);
        alert("Form Submitted Successfully!");

        // Clear the form after submission
        document.getElementById("familyForm").reset();
        document.getElementById("familyMembersContainer").innerHTML = ""; // Clear added members
    });

    // // Handle Login Form Submission
    // document.getElementById("loginForm")?.addEventListener("submit", function (event) {
    //     event.preventDefault();
    //     alert("Login Successful!");
    //     window.location.href = "dashboard.html"; // Redirect to Dashboard
    // });

    document.getElementById("loginForm")?.addEventListener("submit", async function (event) {
        event.preventDefault(); // Prevent default form submission
    
        const formData = new FormData(this);
        const response = await fetch("/login", {
            method: "POST",
            body: formData
        });
    
        if (response.redirected) {
            // Show success message first, then redirect after "OK" is clicked
            alert("Login Successful!");
            window.location.href = response.url;
        } else {
            try {
                const data = await response.json(); // Parse JSON response
                if (data.error) {
                    alert(data.error); // Display error message
                }
            } catch (error) {
                console.error("Error parsing response:", error);
                alert("Incorrect email or password. Please try again.");
            }
        }
    });
    

    

    // Handle Password Reset
    document.getElementById("resetForm")?.addEventListener("submit", function (event) {
        event.preventDefault();
        alert("Password reset link sent!");
        window.location.href = "login.html";
    });

    // Add Member Functionality
    document.getElementById("addMemberBtn")?.addEventListener("click", addMember);
});

function addMember() {
    const container = document.getElementById("familyMembersContainer");

    if (!container) return;

    // Create a wrapper div for each member
    let memberDiv = document.createElement("div");
    memberDiv.classList.add("member-entry");

    // Create Name Input
    let nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.name = "member_name[]";
    nameInput.placeholder = "Family Member Name";
    nameInput.required = true;

    // Create Age Input
    let ageInput = document.createElement("input");
    ageInput.type = "number";
    ageInput.name = "member_age[]";
    ageInput.placeholder = "Year of Birth";
    ageInput.required = true;

    // Create Remove Button (Smaller Width)
    let removeBtn = document.createElement("button");
    removeBtn.innerText = "X"; // Small button with "X" instead of "Remove"
    removeBtn.type = "button";
    removeBtn.classList.add("remove-btn");
    removeBtn.style.width = "40px"; // Adjusted to be smaller
    removeBtn.onclick = function () {
        container.removeChild(memberDiv);
    };

    // Append elements to memberDiv
    memberDiv.appendChild(nameInput);
    memberDiv.appendChild(ageInput);
    memberDiv.appendChild(removeBtn);

    // Append memberDiv to container
    container.appendChild(memberDiv);
}

document.addEventListener("DOMContentLoaded", function() {
    const joinButton = document.querySelector(".join-button");
    joinButton.addEventListener("click", showPopup);
});

function showPopup() {
    document.getElementById("popup").style.display = "flex";
}

function closePopup() {
    document.getElementById("popup").style.display = "none";
}

function alreadyMember() {
    closePopup();
    window.location.href = "/login";
}

function notMember() {
    
    closePopup();
    window.location.href = "/register"; 
}

document.addEventListener("DOMContentLoaded", function () {
    const list = document.querySelector(".our-partners-list"); // Updated class name
    if (list) {
        list.innerHTML += list.innerHTML; // Duplicate logos for smooth loop
    }
});


//register
// document.getElementById("registerForm").addEventListener("submit", function(event) {
//     event.preventDefault();

//     const formData = {
//         name: document.getElementById("name").value,
//         email: document.getElementById("email").value,
//         password: document.getElementById("password").value,
//         city: document.getElementById("city").value,
//         phone: document.getElementById("phone").value,
//         additional_phone: document.getElementById("additional_phone").value || null,
//         family_details: document.getElementById("family_details").value || null,
//         children_count: document.getElementById("children_count").value || 0,
//         interests: document.getElementById("interests").value || null
//     };

//     fetch("http://127.0.0.1:5000/register", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify(formData)
//     })
//     .then(response => response.json())
//     .then(data => {
//         alert(data.message);
//         if (data.message === "User registered successfully!") {
//             window.location.href = "login.html"; // Redirect to login page after successful registration
//         }
//     })
//     .catch(error => console.error("Error:", error));
// });


// //login
// document.getElementById("loginForm").addEventListener("submit", async function (event) {
//     event.preventDefault();

//     const email = document.getElementById("email").value;
//     const password = document.getElementById("password").value;

//     const response = await fetch("http://127.0.0.1:5000/login", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ email, password })
//     });

//     const data = await response.json();

//     if (response.ok) {
//         alert("Login successful!");
//         localStorage.setItem("user", JSON.stringify(data.user)); // Store user info in localStorage
//         window.location.href = "index.html"; // Redirect to dashboard
//     } else {
//         alert(data.error);
//     }
// });
