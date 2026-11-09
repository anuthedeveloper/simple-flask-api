document.querySelectorAll(".auth-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }

    const submitButton = event.submitter || form.querySelector('button[type="submit"]');
    if (!(submitButton instanceof HTMLButtonElement)) {
      return;
    }

    form.dataset.submitting = "true";
    submitButton.disabled = true;
    submitButton.setAttribute("aria-busy", "true");

    const label = submitButton.querySelector("[data-submit-label]");
    if (label) {
      label.textContent = submitButton.dataset.loadingText || "Submitting...";
    }

    const spinner = submitButton.querySelector(".auth-submit-spinner");
    if (spinner) {
      spinner.hidden = false;
    }
  });
});
