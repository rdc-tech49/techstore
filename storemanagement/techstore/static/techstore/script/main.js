
// form validation 
(function () {
	'use strict'
	// Fetch all the forms we want to apply custom Bootstrap validation styles to
	var forms = document.querySelectorAll('.needs-validation')
	// Loop over them and prevent submission
	Array.prototype.slice.call(forms)
		.forEach(function (form) {
			form.addEventListener('submit', function (event) {
				if (!form.checkValidity()) {
					event.preventDefault()
					event.stopPropagation()
				}
				form.classList.add('was-validated')
			}, false)
		})
})()

// message 
  // Wait for the page to fully load
  document.addEventListener("DOMContentLoaded", function () {
    // Select all alert messages
    let alerts = document.querySelectorAll(".alert");

    // Set timeout to remove them after 5 seconds
    alerts.forEach(function (alert) {
      setTimeout(function () {
        alert.classList.remove("show");  // Bootstrap fade effect
        alert.classList.add("fade"); 
        setTimeout(() => alert.remove(), 500); // Remove after fade effect
      }, 5000); // 5000ms = 5 seconds
    });
  });


