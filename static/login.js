

// --------------------------------------
// V0034.0.1 - Login Button Loading Spinner
// --------------------------------------
document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');

  if (!loginForm) {
    return;
  }

  loginForm.addEventListener('submit', function() {
    const submitButton =
      loginForm.querySelector('button[type="submit"]');

    if (!submitButton || submitButton.disabled) {
      return;
    }

    submitButton.disabled = true;

    const spinner =
      submitButton.querySelector('.spinner-border');

    if (spinner) {
      spinner.classList.remove('d-none');
    }

    const textSpan =
      submitButton.querySelector('span:last-child');

    if (textSpan) {
      textSpan.textContent = 'Signing in...';
    } else {
      submitButton.textContent = 'Signing in...';
    }
  });
});