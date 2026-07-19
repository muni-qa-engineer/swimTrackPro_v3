// ================================
// SwimTrack Pro Dashboard Scripts
// Phase: V0015.10 JS Modular Split
// ================================

// ---------- DATE HELPERS ----------
function formatDate(dateObj) {
  const yyyy = dateObj.getFullYear();
  const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
  const dd = String(dateObj.getDate()).padStart(2, '0');

  return `${yyyy}-${mm}-${dd}`;
}

function getTodayDate() {
  return formatDate(new Date());
}

function getWeekDays() {
  return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
}

function getSelectedMonthParts(monthValue) {
  return monthValue.split('-');
}

function getFormattedDay(day) {
  return String(day).padStart(2, '0');
}

function isPastDate(dateObj) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return dateObj < today;
}

// ---------- TOAST HELPERS ----------
function createToast(message, type = 'success', duration = 2000) {
  const toast = document.createElement('div');

  toast.innerText = message;
  toast.classList.add('toast-popup');

  if (type === 'danger') {
    toast.classList.add('toast-danger');
  } else {
    toast.classList.add('toast-success');
  }

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, duration);
}



// ---------- SCROLL POSITION HELPERS ----------
// V0043.x Fix
// Always open pages from the top.
// Previous scroll restoration caused Dashboard,
// Booking, My Bookings and other pages to reopen
// in the middle of the page after navigation.
function saveScrollPosition() {
  // Disabled intentionally.
}

function restoreScrollPosition() {
  window.scrollTo(0, 0);
}


// --------------------------------------
// V0033.5.0 - Auto Logout After Inactivity
// --------------------------------------
// V0033.5.0 - Auto Logout After Inactivity
(function () {
  let inactivityTimer;
  let countdownTimer;
  let countdown = 20;

  const INACTIVITY_MS = 60 * 1000; // 1 minute

  const toast = document.getElementById('inactiveLogoutToast');
  const countdownElement = document.getElementById('logoutCountdown');
  const stayLoggedInBtn = document.getElementById('stayLoggedInBtn');


  if (!toast || !countdownElement || !stayLoggedInBtn) {
    return;
  }

  function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(showLogoutWarning, INACTIVITY_MS);

    // Dismiss the warning and clear the countdown if it is showing
    if (toast.style.display === 'block') {
      toast.style.display = 'none';
      clearInterval(countdownTimer);
    }
  }

  function showLogoutWarning() {
    countdown = 20;
    countdownElement.textContent = countdown;
    toast.style.display = 'block';

    clearInterval(countdownTimer);

    countdownTimer = setInterval(() => {
      countdown--;
      countdownElement.textContent = countdown;

      if (countdown <= 0) {
        clearInterval(countdownTimer);
        window.location.href = '/logout';
      }
    }, 1000);
  }

  function stayLoggedIn() {
    toast.style.display = 'none';
    clearInterval(countdownTimer);
    resetInactivityTimer();
  }

  stayLoggedInBtn.addEventListener('click', stayLoggedIn);

  ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']
    .forEach(eventName => {
      document.addEventListener(
        eventName,
        resetInactivityTimer,
        true
      );
    });

  resetInactivityTimer();
})();


