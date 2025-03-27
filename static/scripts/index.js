window.scrollToSection = function(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        console.log("Scrolling to:", sectionId);
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
        console.error("Section not found:", sectionId);
    }
};

function searchTable(tableId, searchInputId) {
    let input, filter, table, tr, td, i, j, txtValue;
    input = document.getElementById(searchInputId);
    filter = input.value.toLowerCase();
    table = document.getElementById(tableId);
    tr = table.getElementsByTagName("tr");

    for (i = 0; i < tr.length; i++) {
        let rowVisible = false;
        td = tr[i].getElementsByTagName("td");
        for (j = 0; j < td.length; j++) {
            if (td[j]) {
                txtValue = td[j].textContent || td[j].innerText;
                if (txtValue.toLowerCase().indexOf(filter) > -1) {
                    rowVisible = true;
                    break;
                }
            }
        }
        tr[i].style.display = rowVisible ? "" : "none";
    }
}

document.addEventListener("DOMContentLoaded", function () {
    generateCharts();
});

function generateCharts() {
    fetch('/admin')
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");

            // Extract event and city registration data
            let eventData = JSON.parse(doc.getElementById("eventChartData").textContent);
            let cityData = JSON.parse(doc.getElementById("eventCityChartData").textContent);

            // Convert arrays into key-value objects
            let eventChartData = {};
            let eventCityChartData = {};

            eventData.forEach(event => eventChartData[event[0]] = event[1]);
            cityData.forEach(city => eventCityChartData[city[0]] = city[1]);

            console.log("Event Registration Data:", eventChartData); // Debugging
            console.log("Event Registrations by City Data:", eventCityChartData); // Debugging

            // Generate charts
            createPieChart("eventChart", "Event Registrations", eventChartData);
            createPieChart("eventCityChart", "Event Registrations by City", eventCityChartData);
        })
        .catch(error => console.error("Error fetching chart data:", error));
}


function createPieChart(canvasId, title, data) {
    const ctx = document.getElementById(canvasId).getContext("2d");

    // Define pastel colors for the pie chart
    const pastelColors = [
        "#FFB3BA", // Light Pink
        "#FFDFBA", // Light Peach
        "#FFFFBA", // Light Yellow
        "#BAFFC9", // Light Mint Green
        "#BAE1FF", // Light Blue
        "#D0A9F5", // Light Purple
        "#FFABAB", // Pastel Red
        "#A9F1DF", // Pastel Green
        "#F7E4B1", // Pastel Orange
    ];

    new Chart(ctx, {
        type: "pie",
        data: {
            labels: Object.keys(data),
            datasets: [
                {
                    data: Object.values(data),
                    backgroundColor: pastelColors.slice(0, Object.keys(data).length), // Use only required colors
                    borderColor: "#ffffff", // White border for contrast
                    borderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "bottom" },
                title: { display: true, text: title },
            },
        },
    });
}



document.getElementById("exportPDF").addEventListener("click", function () {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Title of the PDF
    doc.setFontSize(14);
    doc.text("Registered Users", 14, 15);

    // Get the table data
    const table = document.getElementById("registrationTable");
    const rows = table.getElementsByTagName("tr");

    // Extract table headers
    let headers = [];
    const headerCells = rows[0].getElementsByTagName("th");
    for (let i = 0; i < headerCells.length; i++) {
        headers.push(headerCells[i].innerText.trim());
    }

    // Extract table rows
    let data = [];
    for (let i = 1; i < rows.length; i++) {
        let rowData = [];
        let cells = rows[i].getElementsByTagName("td");
        for (let j = 0; j < cells.length; j++) {
            rowData.push(cells[j].innerText.trim());
        }
        data.push(rowData);
    }

    // Using autoTable to format table
    doc.autoTable({
        head: [headers],
        body: data,
        startY: 25,
        theme: "grid",
        styles: { fontSize: 10, cellPadding: 2 },
        headStyles: { fillColor: [0, 0, 0], textColor: [255, 255, 255] },
        columnStyles: { 0: { cellWidth: 'auto' } }, // Adjusting first column width dynamically
    });

    // Save the PDF
    doc.save("registered_users.pdf");
});


function fetchEventRegistrations() {
    fetch('/fetch-event-registrations')
    .then(response => response.json())
    .then(data => {
        console.log("Received event registrations:", data); // ✅ Debugging

        const tableBody = document.querySelector("#eventRegistrationTable tbody");
        tableBody.innerHTML = ""; // Clear previous rows

        data.forEach((reg) => {
            console.log(`Mapping Data - Registration ID: ${reg.registration_id}, Event ID: ${reg.event_id}, Name: ${reg.name}, Num People: ${reg.num_people}`); // ✅ Debug log

            let row = document.createElement("tr");

            row.innerHTML = `
                <td>${reg.name || '-'}</td>    
                <td>${reg.email || '-'}</td>
                <td>${reg.phone || '-'}</td>
                <td>${reg.registration_id || '-'}</td>
                <td>${reg.event_id || '-'} </td> <!-- ✅ Correctly mapped -->
                <td>${reg.num_people !== undefined ? reg.num_people : '-'} </td>  <!-- ✅ Correctly mapped -->
            `;

            tableBody.appendChild(row);
        });

        console.log("Table updated successfully!");
    })
    .catch(error => console.error("Error loading registrations:", error));
}


function deleteEvent(eventId) {
    fetch('/delete-event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: eventId })  // Send event ID properly
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Event deleted successfully!");
            location.reload();  // Refresh page after delete
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".delete-btn").forEach(button => {
        button.addEventListener("click", function () {
            const imageId = this.getAttribute("data-id");
            deleteImage(imageId);
        });
    });
});

function deleteImage(imageId) {
    if (!confirm("Are you sure you want to delete this image?")) return;

    fetch(`/delete-image/${imageId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Image deleted successfully!");
            location.reload(); // ✅ Refresh after deletion
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}


//news
window.scrollToSection = function(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
        console.error("Section not found:", sectionId);
    }
};


document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".delete-news-btn").forEach(button => {
        button.addEventListener("click", function () {
            const newsId = this.getAttribute("data-id");
            deleteNews(newsId);
        });
    });
});

function deleteNews(newsId) {
    if (!confirm("Are you sure you want to delete this news article?")) return;

    fetch(`/delete-news/${newsId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("News deleted successfully!");
            location.reload();
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error("Error:", error));
}


window.scrollToSection = function(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
        console.error("Section not found:", sectionId);
    }
};


function deleteEvent(eventId) {
    if (!confirm("Are you sure you want to delete this event?")) return;

    fetch(`/delete-event/${eventId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Event deleted successfully!");
            location.reload();
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(error => console.error("Error:", error));
}
document.addEventListener("DOMContentLoaded", function () {
    fetch("/get-upcoming-event-registrations")
        .then(response => response.json())
        .then(events => {
            const container = document.getElementById("eventRegistrationsContainer");
            container.innerHTML = ""; // Clear previous data

            for (const [eventId, eventData] of Object.entries(events)) {
                let eventBlock = `
                    <div class="event-block">
                        <h4>${eventData.title}</h4>
                        <table>
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Phone</th>
                                    <th>Total People</th>
                                    <th>Adults</th>
                                    <th>Children</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                eventData.registrations.forEach(reg => {
                    eventBlock += `
                        <tr>
                            <td>${reg.user_id}</td>  <!-- Display formatted User ID -->
                            <td>${reg.name}</td>
                            <td>${reg.email}</td>
                            <td>${reg.phone}</td>
                            <td>${reg.num_people}</td>
                            <td>${reg.adults}</td>
                            <td>${reg.children}</td>
                        </tr>
                    `;
                });

                eventBlock += `
                            </tbody>
                        </table>
                        <button onclick="exportUpcomingPDF(${eventId})">Export PDF</button>
                    </div>
                    <hr class="event-separator">  <!-- Adds a horizontal line between events -->
                `;

                container.innerHTML += eventBlock;
            }
        })
        .catch(error => console.error("Error fetching upcoming event registrations:", error));
});

function exportUpcomingPDF(eventId) {
    fetch(`/check-event-category/${eventId}`)
        .then(response => response.json())
        .then(data => {
            if (data.category === "upcoming") {
                window.location.href = `/export-upcoming-event-registrations/${eventId}`;
            } else {
                alert("Export is only allowed for upcoming events!");
            }
        })
        .catch(error => console.error("Error checking event category:", error));
}


document.addEventListener("DOMContentLoaded", function () {
    const editButtons = document.querySelectorAll(".edit-btn");
    const addImagesButtons = document.querySelectorAll(".add-images-btn");
    const editGallerySection = document.getElementById("editGallerySection");
    const addImagesSection = document.getElementById("addImagesSection");
    const editForm = document.getElementById("editGalleryForm");
    const extraImagesForm = document.getElementById("addExtraImagesForm");
    const existingImagesDiv = document.getElementById("existingImages");
    let deletedImages = false;

    // ✅ Show Edit Modal & Fetch Gallery Details
    editButtons.forEach(button => {
        button.addEventListener("click", function () {
            let imageId = this.dataset.id;

            fetch(`/get_gallery_details/${imageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById("editImageId").value = data.id;
                    document.getElementById("editTitle").value = data.title;
                    document.getElementById("editDescription").value = data.description;
                    
                    existingImagesDiv.innerHTML = ""; // Clear old images
                    deletedImages = false;
                    
                    data.extra_images.forEach(img => {
                        let imgElement = document.createElement("div");
                        imgElement.innerHTML = `
                            <img src="/static/${img.file_path}" width="100" height="100">
                            <button class="delete-img-btn" data-id="${img.id}">❌ Remove</button>
                        `;
                        existingImagesDiv.appendChild(imgElement);
                    });

                    editGallerySection.style.display = "block";  // ✅ Show Edit Section
                } else {
                    alert(data.message);
                }
            });
        });
    });

    // ✅ Submit Edit Form & Handle Updates
    editForm.addEventListener("submit", function (event) {
        event.preventDefault();
        
        let formData = new FormData(editForm);

        fetch("/edit_gallery_image", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log("Server Response:", data);  // ✅ Debugging

            if (data.success) {
                alert("Successfully saved changes!");  // ✅ Show success message
                
                // ✅ Update title and description on the page immediately
                document.querySelector(".gallery-details-container h1").innerText = data.title;
                document.querySelector(".gallery-details-container p").innerText = data.description;
                
                // Reload after a delay to reflect changes
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                alert("Error: " + data.message);
            }
        })
        .catch(error => {
            console.error("Error:", error);
        });
    });

    // ✅ Delete Images and Update UI
    existingImagesDiv.addEventListener("click", function (event) {
        if (event.target.classList.contains("delete-img-btn")) {
            let imageId = event.target.dataset.id;

            fetch(`/delete_extra_image/${imageId}`, {
                method: "DELETE"
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    event.target.parentElement.remove();
                    deletedImages = true;  // ✅ Mark image as deleted
                } else {
                    alert(data.message);
                }
            });
        }
    });

    // ✅ Show Add Images Section
    addImagesButtons.forEach(button => {
        button.addEventListener("click", function () {
            let imageId = this.dataset.id;
            document.getElementById("extraImageEventId").value = imageId;
            addImagesSection.style.display = "block";  // ✅ Show Add Images Section
        });
    });

    // ✅ Submit Add Images Form
    extraImagesForm.addEventListener("submit", function (event) {
        event.preventDefault();

        let formData = new FormData(extraImagesForm);
        let eventId = document.getElementById("extraImageEventId").value;

        fetch(`/add_gallery_images/${eventId}`, {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            location.reload();
        })
        .catch(error => {
            console.error("Error:", error);
        });
    });

    // ✅ Close Modals When Clicking Outside
    window.onclick = function (event) {
        if (event.target === editGallerySection) {
            editGallerySection.style.display = "none";
        }
        if (event.target === addImagesSection) {
            addImagesSection.style.display = "none";
        }
    };
});
function filterRegistrations() {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let table = document.getElementById("eventRegistrationTable");
    let rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {
        let titleCell = rows[i].getElementsByTagName("td")[0];
        if (titleCell) {
            let title = titleCell.textContent.toLowerCase();
            rows[i].style.display = title.includes(input) ? "" : "none";
        }
    }
}
document.getElementById("searchInput").addEventListener("keyup", filterRegistrations);
