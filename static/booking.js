(function(){
  const today = getTodayDate();

    const el = document.querySelector('input[name="date"]');

    if (el) {
        el.min = today;

        if (!el.value) {
            el.value = today;
        }
    }
  })();
  const pkg = document.getElementById('packageSelect');
  const endDateDiv = document.getElementById('endDateContainer');

  // CENTRALIZED CONFIG
  const PRICING = {
    DEMO_DAY: 500,
    SINGLE_DAY: 750,
    MONTHLY_PACKAGE: 9000,
    CUSTOM_PACKAGE_BASE: 9000
  };

  const GROUP_DISCOUNTS = {
    1: 0,
    2: 6,
    3: 11,
    4: 16,
    5: 21
};

  // Smart weekday validation based on selected Start Date
  const dayCheckboxes = document.querySelectorAll('.class-day');
  const selectedDaysPreview = document.getElementById('selectedDaysPreview');
  const selectedDaysInput = document.getElementById('selectedDaysInput');
  const feeInput = document.getElementById('feeInput');

  function updateAllowedDays() {
    const startDateInput = document.querySelector('input[name="date"]');
    const endDateInput = document.querySelector('input[name="end_date"]');

    if (!startDateInput || !startDateInput.value) return;

    const selectedDate = new Date(startDateInput.value);

    const days = [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday'
    ];

    const allowedDay = days[selectedDate.getDay()];

    if (pkg.value === 'Single' || pkg.value === 'Demo') {
      dayCheckboxes.forEach(cb => {
        cb.checked = false;

        if (cb.value === allowedDay) {
          cb.disabled = false;
          cb.checked = true;
          selectedDaysInput.value = allowedDay;
        } else {
          cb.disabled = true;
        }
      });

      endDateDiv.style.display = 'none';
    }
    else {
      dayCheckboxes.forEach(cb => {
        cb.disabled = false;
      });

      endDateDiv.style.display = 'block';

      if (pkg.value === 'Monthly') {
        const autoEndDate = new Date(selectedDate);
        autoEndDate.setMonth(autoEndDate.getMonth() + 1);
        autoEndDate.setDate(autoEndDate.getDate() - 1);

        endDateInput.value = formatDate(autoEndDate);
      }
      else if (pkg.value === 'Custom') {
        endDateInput.value = startDateInput.value;
      }
    }

    updateSelectedDays();
  }


  function updateSelectedDays() {
    const selected = [];
    const personsInput = document.getElementById('personsInput');
    const persons = Number(personsInput?.value || 1);

    dayCheckboxes.forEach(cb => {
      if (cb.checked) {
        selected.push(cb.value);
      }
    });

    if (pkg.value === 'Monthly' && selected.length > 3) {
      alert('Monthly package allows maximum 3 class days');

      const lastChecked = selected[selected.length - 1];

      dayCheckboxes.forEach(cb => {
        if (cb.value === lastChecked) {
          cb.checked = false;
        }
      });

      return updateSelectedDays();
    }

    // Insert: Monthly package must have 2 or 3 days
    if (pkg.value === 'Monthly' && selected.length === 1) {
      feeInput.value = '';
      feeInput.placeholder = 'Select 2 or 3 class days';
      return;
    }

    if (pkg.value === 'Custom' && selected.length > 5) {
      alert('Maximum 5 class days allowed for Custom package');

      const lastChecked = selected[selected.length - 1];

      dayCheckboxes.forEach(cb => {
        if (cb.value === lastChecked) {
          cb.checked = false;
        }
      });

      return updateSelectedDays();
    }

    selectedDaysInput.value = selected.join(', ');

    selectedDaysPreview.innerText = selected.length
      ? selected.join(', ')
      : 'No days selected';

    if (persons > 5) {
      alert('Maximum 5 persons allowed.');

      if (personsInput) {
        personsInput.value = 5;
      }

      return updateSelectedDays();
    }

    const discountMap = {
        1: 0,
        2: 6,
        3: 11,
        4: 16,
        5: 21
    };

    const discountPercent = discountMap[persons] || 0;
    let actualAmount = 0;

    if (pkg.value === 'Demo') {
      actualAmount = 500 * persons;
    }
    else if (pkg.value === 'Single') {
      actualAmount = 750 * persons;
    }
    else if (pkg.value === 'Monthly') {
      if (selected.length < 2 || selected.length > 3) {
        feeInput.value = '';
        feeInput.placeholder = 'Select 2 or 3 class days';
        return;
      }

      if (selected.length === 2) {
        actualAmount = 6000 * persons;
      }
      else {
        actualAmount = 9000 * persons;
      }
    }
    else if (pkg.value === 'Custom') {
      const startDateInput = document.querySelector('input[name="date"]');
      const endDateInput = document.querySelector('input[name="end_date"]');

      if (!startDateInput.value || !endDateInput.value || selected.length === 0) {
        feeInput.value = 0;
        feeInput.placeholder = '';
        return;
      }

      const start = new Date(startDateInput.value + 'T00:00:00');
      const end = new Date(endDateInput.value + 'T00:00:00');

      const durationDays =
        Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;

      const dayMap = {
        'Sunday': 0,
        'Monday': 1,
        'Tuesday': 2,
        'Wednesday': 3,
        'Thursday': 4,
        'Friday': 5,
        'Saturday': 6
      };

      const selectedDayIndexes = selected.map(day => dayMap[day]);

      let totalClasses = 0;
      const current = new Date(start);

      while (current <= end) {
        if (selectedDayIndexes.includes(current.getDay())) {
          totalClasses++;
        }
        current.setDate(current.getDate() + 1);
      }

      const monthlyCustomFees = {
        1: 3000,
        2: 6000,
        3: 9000,
        4: 11000,
        5: 12000
      };

      const twoMonthCustomFees = {
        1: 6000,
        2: 12000,
        3: 18000,
        4: 22000,
        5: 24000
      };

      const selectedDaysPerWeek = selected.length;

      if (durationDays >= 1 && durationDays <= 23) {
        actualAmount = totalClasses * 750 * persons;
      }
      else if (durationDays >= 24 && durationDays <= 30) {
        actualAmount =
          (monthlyCustomFees[selectedDaysPerWeek] || 0) * persons;
      }
      else if (durationDays >= 31 && durationDays <= 53) {
        actualAmount = totalClasses * 650 * persons;
      }
      else if (durationDays >= 54 && durationDays <= 60) {
        actualAmount =
          (twoMonthCustomFees[selectedDaysPerWeek] || 0) * persons;
      }
      else {
        feeInput.value = '';
        feeInput.placeholder = 'Maximum 60 days allowed';
        return;
      }
    }

    const finalFee = Math.round(
      actualAmount * (100 - discountPercent) / 100
    );

    feeInput.placeholder = '';
    feeInput.value = finalFee;
  }


function handlePackageChange() {
  dayCheckboxes.forEach(cb => {
    cb.checked = false;
  });

  updateAllowedDays();
}

const startDateInput = document.querySelector('input[name="date"]');

const timeSelect = document.getElementById('timeSelect');


function generateTimeSlots() {
  if (!timeSelect) return;

  timeSelect.innerHTML = '';

  const startHour = 6;
  const endHour = 21;

  const selectedDateInput = document.querySelector('input[name="date"]');
  const selectedDate = selectedDateInput ? selectedDateInput.value : '';

  const now = new Date();

  for (let hour = startHour; hour <= endHour; hour++) {
    for (let min of [0, 30]) {

      if (hour === endHour && min > 0) {
        continue;
      }

      const slotDate = new Date();

      if (selectedDate) {
        slotDate.setFullYear(
          Number(selectedDate.split('-')[0]),
          Number(selectedDate.split('-')[1]) - 1,
          Number(selectedDate.split('-')[2])
        );
      }

      slotDate.setHours(hour, min, 0, 0);

      const option = document.createElement('option');

      const displayHour = hour % 12 || 12;
      const displayMin = String(min).padStart(2, '0');
      const ampm = hour >= 12 ? 'PM' : 'AM';

      const label = `${String(displayHour).padStart(2, '0')}:${displayMin} ${ampm}`;

      option.value = label;
      option.textContent = label;

      const isToday = selectedDate === getTodayDate();

      if (isToday && slotDate <= now) {
        option.disabled = true;
      }

      timeSelect.appendChild(option);
    }
  }

  const enabledOption = [...timeSelect.options].find(opt => !opt.disabled);

  if (enabledOption) {
    enabledOption.selected = true;
  }
}


function handleStartDateChange() {
  updateAllowedDays();
  generateTimeSlots();
  checkLocationConflict();

  if (pkg && pkg.value === 'Custom' && startDateInput && endDateInput) {
    const start = new Date(startDateInput.value + 'T00:00:00');

    if (!isNaN(start)) {
      const maxEndDate = new Date(start);
      maxEndDate.setDate(maxEndDate.getDate() + 59);

      endDateInput.max = formatDate(maxEndDate);

      if (endDateInput.value && endDateInput.value > endDateInput.max) {
        endDateInput.value = endDateInput.max;
      }
    }
  }
}

const endDateInput = document.querySelector('input[name="end_date"]');
const personsInput = document.getElementById('personsInput');


function initializeBookingEventListeners() {

  if (pkg) {
    pkg.addEventListener('change', handlePackageChange);
  }

  if (startDateInput) {
    startDateInput.addEventListener('change', handleStartDateChange);
  }

  if (endDateInput) {
    endDateInput.addEventListener('change', updateSelectedDays);
  }

  if (personsInput) {
    personsInput.addEventListener('input', updateSelectedDays);
  }

  if (dayCheckboxes.length > 0) {
    dayCheckboxes.forEach(cb => {
      cb.addEventListener('change', updateSelectedDays);
    });
  }

    const locationInput = document.querySelector('input[name="location"]');

  if (timeSelect) {
    timeSelect.addEventListener('change', checkLocationConflict);
  }

  if (startDateInput) {
    startDateInput.addEventListener('change', checkLocationConflict);
  }

  if (locationInput) {
    locationInput.addEventListener('input', checkLocationConflict);
    locationInput.addEventListener('change', checkLocationConflict);
  }
}

initializeBookingEventListeners();
updateAllowedDays();
generateTimeSlots();
const tabBookings = document.getElementById('tabBookings');
const tabBook = document.getElementById('tabBook');
const tabCalendar = document.getElementById('tabCalendar');

const bookingsSection = document.getElementById('bookingsSection');
const bookSlotSection = document.getElementById('bookSlotSection');
const calendarSection = document.getElementById('calendarSection');

const calendarMonthInput = document.getElementById('calendarMonthInput');
const calendarGrid = document.getElementById('calendarGrid');
// const swimmerRows = document.querySelectorAll('.swimmer-row');
const studentSelect = document.getElementById('studentSelect');


function checkLocationConflict() {
  // Trainer availability is global. Check every booking regardless of owner.
  const bookings = window.allBookingsData || window.bookingsData || [];
  if (!Array.isArray(bookings) || bookings.length === 0) {
    return;
  }
  const dateInput = document.querySelector('input[name="date"]');
  const locationInput = document.querySelector('input[name="location"]');
  const timeSelect = document.getElementById('timeSelect');
  const confirmBookingBtn = document.getElementById('confirmBookingBtn');
  const warning = document.getElementById('locationConflictWarning');

  if (!dateInput || !locationInput || !timeSelect || !confirmBookingBtn || !warning) {
    return;
  }

  const selectedDate = (dateInput.value || '').trim();
  const selectedTime = (timeSelect.value || '').trim();
  const selectedLocation = (locationInput.value || '').trim().toLowerCase();

  // Helper to convert "06:30 AM" to minutes since midnight
  function parseTimeToMinutes(t) {
    if (!t) return null;
    // Expects format "hh:mm AM/PM"
    const match = t.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
    if (!match) return null;
    let hour = parseInt(match[1], 10);
    const min = parseInt(match[2], 10);
    const ampm = match[3].toUpperCase();
    if (ampm === 'PM' && hour !== 12) hour += 12;
    if (ampm === 'AM' && hour === 12) hour = 0;
    return hour * 60 + min;
  }

  // Hide warning and info if not all required fields
  if (!selectedDate || !selectedTime || !selectedLocation) {
    warning.style.display = 'none';
    const info = document.getElementById('groupSessionInfo');
    if (info) info.style.display = 'none';
    updateSwimmerBookingState();
    return;
  }

  const selectedTimeMinutes = parseTimeToMinutes(selectedTime);
  if (selectedTimeMinutes === null) {
    warning.style.display = 'none';
    const info = document.getElementById('groupSessionInfo');
    if (info) info.style.display = 'none';
    updateSwimmerBookingState();
    return;
  }

  let locationConflict = false;
  let groupSwimmers = new Set();

  for (const booking of bookings) {
    // Use calendar_dates (array) if present, else skip
    const calendarDates = Array.isArray(booking.calendar_dates) ? booking.calendar_dates : [];
    if (!calendarDates.includes(selectedDate)) continue;
    const bookingTime = String(booking.time || '').trim();
    const bookingTimeMinutes = parseTimeToMinutes(bookingTime);
    if (bookingTimeMinutes === null) continue;
    const minuteDiff = Math.abs(bookingTimeMinutes - selectedTimeMinutes);
    if (minuteDiff >= 60) continue; // Only check if time diff is less than 60
    const bookingLocation = String(booking.location || '').trim().toLowerCase();
    if (bookingLocation !== selectedLocation) {
      // Location conflict
      locationConflict = true;
      break;
    } else {
      // Same location, group session
      if (booking.student) {
        groupSwimmers.add(booking.student);
      }
    }
  }

  // Remove current swimmer (if present) from groupSwimmers (i.e., don't show own name)
  // Only used for group session info, not for location conflict detection.
  const studentSelect = document.getElementById('studentSelect');
  let currentSwimmer = '';
  if (studentSelect) {
    if (studentSelect.tagName === 'INPUT') {
      currentSwimmer = studentSelect.value.trim();
    } else if (studentSelect.tagName === 'SELECT') {
      currentSwimmer = studentSelect.value.trim();
    }
  }
  if (currentSwimmer) groupSwimmers.delete(currentSwimmer);

  const info = document.getElementById('groupSessionInfo');

  if (locationConflict) {
    warning.style.display = 'block';
    confirmBookingBtn.disabled = true;
    // Hide group info if present
    if (info) info.style.display = 'none';
    return;
  } else {
    warning.style.display = 'none';
    confirmBookingBtn.disabled = false;

    // Show info about group swimmers if any
    if (groupSwimmers.size > 0) {
      // Create or update info alert
      let infoAlert = info;
      if (!infoAlert) {
        // Insert after warning
        infoAlert = document.createElement('div');
        infoAlert.id = 'groupSessionInfo';
        infoAlert.className = 'alert alert-info mt-2';
        warning.parentNode.insertBefore(infoAlert, warning.nextSibling);
      }
      infoAlert.style.display = 'block';
      const names = Array.from(groupSwimmers);
      if (names.length === 1) {
        infoAlert.textContent = `You are swimming along with ${names[0]}.`;
      } else if (names.length > 1) {
        infoAlert.textContent = `You are swimming along with ${names[0]}, ${names[1]} and ${names.length - 2} others.`;
      }
    } else {
      // Hide/remove info alert if present
      if (info) info.style.display = 'none';
    }

    updateSwimmerBookingState();
  }
}

function resetBookingForm() {
  if (bookingForm) {
    bookingForm.reset();
  }

  if (studentSelect) {
    studentSelect.value = '';
  }

  if (startDateInput) {
    startDateInput.value = getTodayDate();
  }

  if (endDateInput) {
    endDateInput.value = '';
  }

  dayCheckboxes.forEach(cb => {
    cb.checked = false;
  });

  if (selectedDaysInput) {
    selectedDaysInput.value = '';
  }

  if (selectedDaysPreview) {
    selectedDaysPreview.innerText = 'No days selected';
  }

  if (feeInput) {
    feeInput.value = 0;
  }

  if (pkg) {
    pkg.value = 'Single';
  }

  localStorage.removeItem('activeSwimmer');

  updateAllowedDays();
  generateTimeSlots();
}

if (swimmerAddForm && swimmerNameInput) {
  swimmerAddForm.addEventListener('submit', () => {
    localStorage.setItem('activeSwimmer', swimmerNameInput.value.trim());
    localStorage.setItem('activeTab', 'book_slot');
    localStorage.setItem('swimmerAdded', 'true');
  });
}

if (bookingForm) {
  bookingForm.addEventListener('submit', (event) => {
    const confirmBookingBtn = document.getElementById('confirmBookingBtn');
    const confirmBookingSpinner = document.getElementById('confirmBookingSpinner');
    const confirmBookingText = document.getElementById('confirmBookingText');

    // Monthly package requires exactly 2 or 3 selected class days.
    if (pkg && pkg.value === 'Monthly') {
      const selectedCount = document.querySelectorAll('.class-day:checked').length;

      if (selectedCount < 2 || selectedCount > 3) {
        event.preventDefault();

        createToast(
          'Monthly package requires selecting 2 or 3 class days.',
          'danger',
          3000
        );

        return;
      }
    }

    // Show loading state immediately to prevent duplicate clicks.
    if (confirmBookingBtn) {
      confirmBookingBtn.disabled = true;
    }

    if (confirmBookingSpinner) {
      confirmBookingSpinner.classList.remove('d-none');
    }

    if (confirmBookingText) {
      confirmBookingText.textContent = 'Processing...';
    }

    localStorage.setItem('activeTab', 'bookings');
    // REMOVED the setTimeout that was clearing form parameters prematurely!
  });
}

window.addEventListener('load', () => {
  restoreScrollPosition();
  sessionStorage.removeItem('dashboardScrollY');
  const swimmerAdded = localStorage.getItem('swimmerAdded');
  const urlParams = new URLSearchParams(window.location.search);
  const swimmerExists = urlParams.get('swimmer_exists');
  const bookingConflict = window.location.search.includes('booking_conflict');
  // const locationConflict = window.location.search.includes('location_conflict');
  const bookingSuccess = window.location.search.includes('booking_success');

  if (bookingSuccess) {
  createToast(
    '<i class="fa-solid fa-circle-check"></i> Booking created successfully.',
    'success',
    3000
  );

  window.history.replaceState(
    {},
    document.title,
    window.location.pathname
  );
}

  if (bookingConflict) {
    createToast(
      '<i class="fa-solid fa-triangle-exclamation"></i> Duplicate booking already exists for this swimmer.',
      'danger',
      4000
    );

    localStorage.removeItem('bookingSuccess');
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // if (locationConflict) {
  //   createToast(
  //     '<i class="fa-solid fa-triangle-exclamation"></i> Selected time slot is already booked at another location.',
  //     'danger',
  //     4000
  //   );

  //   window.history.replaceState({}, document.title, window.location.pathname);
  // }

  if (swimmerExists === 'true') {
    createToast('<i class="fa-solid fa-triangle-exclamation"></i> Swimmer already exists', 'danger', 2000);
    window.history.replaceState({}, document.title, window.location.pathname);
  }
});
  if (calendarMonthInput) {
    calendarMonthInput.addEventListener('change', renderCalendar);
  }

// Disable booking if no swimmers are available

function updateSwimmerBookingState() {
  const studentSelect = document.getElementById('studentSelect');
  const confirmBookingBtn = document.getElementById('confirmBookingBtn');

  if (!confirmBookingBtn) {
    return;
  }

  // V0040 booking page uses an INPUT, not a SELECT.
  if (studentSelect && studentSelect.tagName === 'INPUT') {
    const warning = document.getElementById('noSwimmersWarning');

    if (warning) {
      warning.remove();
    }

    confirmBookingBtn.disabled = !studentSelect.value.trim();
    return;
  }

  if (!studentSelect) {
    return;
  }

  const hasValidOptions = Array.from(studentSelect.options || []).some(option => {
    return option.value && option.value.trim() !== '';
  });

  let warning = document.getElementById('noSwimmersWarning');

  if (!hasValidOptions) {
    confirmBookingBtn.disabled = true;

    if (!warning) {
      warning = document.createElement('div');
      warning.id = 'noSwimmersWarning';
      warning.className = 'alert alert-warning mt-2';
      warning.textContent = 'Add a swimmer to book a slot.';
      studentSelect.parentElement.appendChild(warning);
    }
  } else {
    const conflictWarning = document.getElementById('locationConflictWarning');

    if (!conflictWarning || conflictWarning.style.display === 'none') {
      confirmBookingBtn.disabled = false;
    }

    if (warning) {
      warning.remove();
    }
  }
}



window.addEventListener('load', updateSwimmerBookingState);

// V0040.5 - Quick Action Navigation
const quickBookBtn = document.getElementById('quickBookBtn');
if (quickBookBtn) {
  quickBookBtn.addEventListener('click', () => {
    window.location.href = '/booking';
  });
}

const quickBookingsBtn = document.getElementById('quickBookingsBtn');
if (quickBookingsBtn) {
  quickBookingsBtn.addEventListener('click', () => {
    window.location.href = '/my-bookings';
  });
}

const quickPaymentsBtn = document.getElementById('quickPaymentsBtn');
if (quickPaymentsBtn) {
  quickPaymentsBtn.addEventListener('click', () => {
    window.location.href = '/payments';
  });
}

// V0042.0.2 - Open Full Calendar Navigation
const openFullCalendarBtn = document.getElementById('openFullCalendarBtn');
if (openFullCalendarBtn) {
  openFullCalendarBtn.addEventListener('click', () => {
    window.location.href = '/calendar';
  });
}


const bookingStudentInput = document.getElementById('studentSelect');

if (bookingStudentInput && bookingStudentInput.tagName === 'INPUT') {
  bookingStudentInput.addEventListener('input', updateSwimmerBookingState);
}


// --------------------------------------
// V0034.0.1 - Generic Form Loading Helper
// Used for Update Notice Board spinner.
// --------------------------------------
function enableFormLoading(formId, loadingText) {
  const form = document.getElementById(formId);

  if (!form) {
    return;
  }

  form.addEventListener('submit', function() {
    const submitButton = form.querySelector('button[type="submit"]');

    if (!submitButton || submitButton.disabled) {
      return;
    }

    submitButton.disabled = true;

    const spinner = submitButton.querySelector('.spinner-border');
    if (spinner) {
      spinner.classList.remove('d-none');
    }

    const textSpan =
      submitButton.querySelector('#updateNoticeText') ||
      submitButton.querySelector('span:last-child');

    if (textSpan) {
      textSpan.textContent = loadingText;
    } else {
      submitButton.textContent = loadingText;
    }
  });
}

// Enable loading animation for the trainer Notice Board form.
enableFormLoading('updateNoticeForm', 'Updating...');


