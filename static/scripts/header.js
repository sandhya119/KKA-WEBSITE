class CustomNavbar extends HTMLElement {
    constructor() {
        super();

        // Get Flask URLs from the HTML attributes
        const homeURL = this.dataset.home;
        const aboutURL = this.dataset.about;
        const newsURL = this.dataset.news;
        const pastEventsURL = this.dataset.pastEvents;
        const upcomingEventsURL = this.dataset.upcomingEvents;
        const galleryURL = this.dataset.gallery;
        const contactURL = this.dataset.contact;
        const logoURL = this.dataset.logo;
        const menuIconURL = this.dataset.menuIcon;

        // Check user session using a global JS variable set in the Flask template
        const isAuthenticated = this.dataset.authenticated === "true"; // Flask will pass "true" or "false"
        const profileURL = this.dataset.profile;
        const logoutURL = this.dataset.logout;
        const loginURL = this.dataset.login;


        this.innerHTML = `
            <header>
                <nav class="navbar">
                    <div class="logo">
                        <a href="${homeURL}">
                            <img src="${logoURL}" alt="Logo">
                        </a>
                    </div>
                    <div class="menu-toggle">
                        <img src="${menuIconURL}" alt="Menu">
                    </div>
                    <ul class="nav-links">
                        <li><a href="${homeURL}">Home</a></li>
                        <li><a href="${aboutURL}">About Us</a></li>
                        <li><a href="${newsURL}">News</a></li>
                        <li class="dropdown">
                            <button class="dropbtn">Events</button>
                            <ul class="dropdown-content">
                                <li><a href="${pastEventsURL}">Past Events</a></li>
                                <li><a href="${upcomingEventsURL}">Upcoming Events</a></li>
                            </ul>
                        </li>
                        <li><a href="${galleryURL}">Gallery</a></li>
                        <li><a href="${contactURL}" class="contact-link">Contact</a></li>
                        <li><button class="join-button">Join</button></li>
                    </ul>
                    <div class="auth-links">
                        ${
                            isAuthenticated
                                ? `<a href="${profileURL}" class="action-button">Profile</a>
                                   <button class="action-button" id="logout-btn">Logout</button>`
                                : `<a href="${loginURL}" class="action-button">Login</a>`
                        }
                    </div>
                </nav>
            </header>
        `;

        // Get necessary elements
        const menuToggle = this.querySelector('.menu-toggle');
        const navLinks = this.querySelector('.nav-links');
        const dropdownButton = this.querySelector('.dropbtn');
        const dropdownMenu = this.querySelector('.dropdown-content');
        const joinButton = this.querySelector('.join-button');
        const contactLink = this.querySelector('.contact-link');
        const logoutButton = this.querySelector('#logout-btn'); // Logout button

        // Toggle mobile menu
        if (menuToggle) {
            menuToggle.addEventListener('click', () => {
                navLinks.classList.toggle('active');
            });
        }

        // Dropdown toggle for "Events"
        if (dropdownButton) {
            dropdownButton.addEventListener('click', (event) => {
                event.stopPropagation(); // Prevent event from bubbling to window
                dropdownMenu.classList.toggle('show');
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (event) => {
            if (!dropdownButton.contains(event.target) && !dropdownMenu.contains(event.target)) {
                dropdownMenu.classList.remove('show');
            }
        });

        // Close menu when clicking "Join" on mobile
        // if (joinButton) {
        //     joinButton.addEventListener('click', () => {
        //         if (window.innerWidth <= 768) {
        //             navLinks.classList.remove('active');
        //         }
        //     });
        // }

        // Contact page event listener (Scroll or Redirect)
        if (contactLink) {
            contactLink.addEventListener("click", (event) => {
                event.preventDefault(); // Stop default link behavior

                const contactSection = document.getElementById("contact");

                if (contactSection) {
                    // Smooth scroll if "contact" section exists
                    contactSection.scrollIntoView({ behavior: "smooth" });
                } else {
                    // Redirect to the contact page
                    window.location.href = contactURL;
                }
            });
        }
        // Handle Logout Button click
        if (logoutButton) {
            logoutButton.addEventListener('click', () => {
                // Perform logout action (e.g., redirect to Flask logout route)
                window.location.href = logoutURL; // Redirect to logout route (Flask endpoint)
            });
        }
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const popup = document.getElementById("popup");
    const joinButton = document.querySelector(".join-button");
    const closeButton = document.querySelector(".close-btn");

    if (popup) {
        popup.style.display = "none"; // Ensure it's hidden on page load
    }

    if (joinButton) {
        joinButton.addEventListener("click", function () {
            popup.style.display = "flex"; // Show the popup when Join is clicked
        });
    }

    if (closeButton) {
        closeButton.addEventListener("click", function () {
            popup.style.display = "none"; // Hide popup on close
        });
    }
});

function alreadyMember() {
    closePopup();
    window.location.href = "/login";
}

function notMember() {
    closePopup();
    window.location.href = "/register";
}

function closePopup() {
    document.getElementById("popup").style.display = "none";
}

// Define the custom element
customElements.define("custom-navbar", CustomNavbar);