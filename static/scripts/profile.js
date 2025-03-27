document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("profileForm").addEventListener("submit", function (event) {
        event.preventDefault();

        let formData = new FormData(this);

        fetch("/update_profile", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.success) {
                location.reload();
            }
        })
        .catch(error => console.error("Error:", error));
    });
});
document.querySelector('.profile-btn').addEventListener('click', function () {
    document.querySelector('.dropdown-menu').classList.toggle('show');
});
