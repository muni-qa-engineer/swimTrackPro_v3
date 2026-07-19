function showBookings() {
  bookingsSection.style.display = 'block';
  if (bookSlotSection) {
    bookSlotSection.style.display = 'none';
  }
  calendarSection.style.display = 'none';

  tabBookings.classList.add('active');
  if (tabBook) {
    tabBook.classList.remove('active');
  }
  tabCalendar.classList.remove('active');

  localStorage.setItem('activeTab', 'bookings');
}


function showBookSlot() {
  bookingsSection.style.display = 'none';
  if (bookSlotSection) {
    bookSlotSection.style.display = 'flex';
  }
  calendarSection.style.display = 'none';

  if (tabBook) {
    tabBook.classList.add('active');
  }
  tabBookings.classList.remove('active');
  tabCalendar.classList.remove('active');

  localStorage.setItem('activeTab', 'book_slot');
}


function showCalendar() {
  bookingsSection.style.display = 'none';
  if (bookSlotSection) {
    bookSlotSection.style.display = 'none';
  }
  calendarSection.style.display = 'block';

  tabCalendar.classList.add('active');
  tabBookings.classList.remove('active');
  if (tabBook) {
    tabBook.classList.remove('active');
  }

  localStorage.setItem('activeTab', 'calendar');

  const today = new Date();

  if (!calendarMonthInput.value) {
    calendarMonthInput.value = formatDate(today).slice(0, 7);
  }

  renderCalendar();
}

// Payment summary calculation support

function renderCalendar() {

  if (!calendarMonthInput || !calendarGrid) return;

  const selectedMonth = calendarMonthInput.value;

  if (!selectedMonth) return;

  const [year, month] = getSelectedMonthParts(selectedMonth);

  const totalDays = new Date(year, month, 0).getDate();
  const weekDays = getWeekDays();

  const bookings = window.bookingsData || [];

  calendarGrid.innerHTML = '';

  const firstDayIndex = new Date(year, month - 1, 1).getDay();
  const totalCells = 42;

  for (let cellIndex = 0; cellIndex < totalCells; cellIndex++) {
    const day = cellIndex - firstDayIndex + 1;

    // Empty cells before the first day and after the last day
    if (day < 1 || day > totalDays) {
      const emptyCell = document.createElement('div');
      emptyCell.className = 'calendar-empty-cell';
      calendarGrid.appendChild(emptyCell);
      continue;
    }

    const formattedDay = getFormattedDay(day);
    const fullDate = `${year}-${month}-${formattedDay}`;

    const currentDate = new Date(fullDate);
    const dayName = weekDays[currentDate.getDay()];
    const isPastDay = isPastDate(currentDate);

    const dayBookings = bookings.filter(b => {
      const recurringDates = b.calendar_dates || [];
      return recurringDates.includes(fullDate);
    });

    // --------------------------------------
    // V0033.0 Step 12.1 - Add standalone make-up request events
    // --------------------------------------
    const standaloneMakeupEvents = [];

    bookings.forEach(booking => {
      if (!Array.isArray(booking.makeup_requests)) {
        return;
      }

      booking.makeup_requests.forEach(request => {
        // Skip if the requested date is already part of the
        // regular booking schedule.
        const isRegularBookingDate =
          Array.isArray(booking.calendar_dates) &&
          booking.calendar_dates.includes(request.requested_date);

        if (isRegularBookingDate) {
          return;
        }

        // Only render on the requested replacement date.
        if (request.requested_date !== fullDate) {
          return;
        }

        // Create a temporary booking-like object so the existing
        // rendering and modal logic can be reused.
        standaloneMakeupEvents.push({
          ...booking,
          calendar_dates: [request.requested_date],
          pending_request_id:
            request.status === 'pending' ? request.id : '',
          makeup_requests: [request]
        });
      });
    });

    // Merge standalone make-up events into this day's events.
    dayBookings.push(...standaloneMakeupEvents);

    const card = document.createElement('div');
    card.className = 'col-md-2 col-sm-3 col-6';

    card.innerHTML = `
      <div class="border rounded p-2 h-100 shadow-sm ${isPastDay ? 'bg-light text-muted opacity-50' : 'bg-light'}">

        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="fw-bold text-primary">${day}</div>
          <div class="small fw-semibold text-secondary">${dayName}</div>
        </div>

        <div class="calendar-events"></div>
      </div>
    `;

    calendarGrid.appendChild(card);

    const eventsContainer = card.querySelector('.calendar-events');

    if (dayBookings.length === 0) {
      eventsContainer.innerHTML = '<div class="small text-muted">No Bookings</div>';
      continue;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const eventDate = new Date(fullDate);
    eventDate.setHours(0, 0, 0, 0);

    const isPastSession = eventDate < today;

    dayBookings.forEach(booking => {

      const bookingDiv = document.createElement('div');
      bookingDiv.className = 'calendar-booking calendar-session';
      bookingDiv.style.cursor = 'pointer';
      bookingDiv.title = 'Click to open session options';

      // Data used by the calendar modal in dashboard.html
      bookingDiv.dataset.bookingId = booking.id || '';
      bookingDiv.dataset.student = booking.student || '';
      bookingDiv.dataset.package = booking.package || booking.package_type || '';
      bookingDiv.dataset.sessionDate = fullDate;
      // --------------------------------------
      // V0033.0 Step 9 - Available Make-Up Credit
      // --------------------------------------
      bookingDiv.dataset.availableMakeupCreditId =
        booking.available_makeup_credit_id || '';

      bookingDiv.dataset.hasAvailableMakeupCredit =
        booking.has_available_makeup_credit ? 'true' : 'false';
      bookingDiv.dataset.endDate = booking.end_date || '';
      bookingDiv.dataset.pendingRequestId =
        booking.pending_request_id || '';

      // --------------------------------------
      // V0033.0 Step 7 - Skip Eligibility Rules
      // --------------------------------------
      const packageType = booking.package || booking.package_type || '';
      const scheduledClasses = (booking.calendar_dates || []).length;

      // Count already-used skip credits for this booking from the data
      // loaded on the page, if available.
      const usedSkips = Number(booking.makeup_credits_used || 0);

      let maxSkips = 0;
      let validUntil = '';

      if (packageType === 'Monthly') {
        // Monthly package: maximum 2 skips.
        maxSkips = 2;

        // Valid until package end date + 5 days.
        if (booking.end_date) {
          const expiry = new Date(booking.end_date + 'T00:00:00');
          expiry.setDate(expiry.getDate() + 5);
          validUntil = formatDate(expiry);
        }
      } else if (packageType === 'Custom') {
        // Custom package: 1 skip for every 7 scheduled classes.
        maxSkips = Math.floor(scheduledClasses / 7);

        // Valid within 3 days from the skipped date.
        const sessionDateObj = new Date(fullDate + 'T00:00:00');
        sessionDateObj.setDate(sessionDateObj.getDate() + 3);
        validUntil = formatDate(sessionDateObj);
      }

      const skipRemaining = Math.max(0, maxSkips - usedSkips);

      bookingDiv.dataset.skipRemaining = String(skipRemaining);
      bookingDiv.dataset.validUntil = validUntil;
      bookingDiv.dataset.skipEligible = skipRemaining > 0 ? 'true' : 'false';

      if (isPastSession) {
        bookingDiv.classList.add('past-session');
      }

      // --------------------------------------
      // V0033.0 Step 10 - Calendar Status Indicators
      // --------------------------------------
      let statusLines = [];

      // Show "Skipped" on the original skipped session date.
      if (Array.isArray(booking.skipped_dates) &&
          booking.skipped_dates.includes(fullDate)) {
        statusLines.push(
          '<div class="small text-warning fw-semibold"><i class="fa-solid fa-diamond text-warning"></i> Skipped</div>'
        );
      }

      // Show pending/approved/rejected on requested replacement dates.
      if (Array.isArray(booking.makeup_requests)) {
        booking.makeup_requests.forEach(request => {
          if (request.requested_date !== fullDate) {
            return;
          }

          if (request.status === 'pending') {
            statusLines.push(
              '<div class="small text-warning fw-semibold"><i class="fa-solid fa-circle text-warning"></i> Pending Approval</div>'
            );
          } else if (request.status === 'approved') {
            statusLines.push(
              '<div class="small text-success fw-semibold"><i class="fa-solid fa-circle text-success"></i> Approved</div>'
            );
          } else if (request.status === 'rejected') {
            statusLines.push(
              '<div class="small text-danger fw-semibold"><i class="fa-solid fa-circle text-danger"></i> Rejected</div>'
            );
          }
        });
      }

      bookingDiv.innerHTML =
        `🏊 ${booking.student} • <i class="fa-regular fa-clock"></i> ${booking.time || 'N/A'}` +
        (statusLines.length ? `<br>${statusLines.join('')}` : '');

      const existingEvents = eventsContainer.querySelectorAll('.calendar-booking');

      const duplicateExists = Array.from(existingEvents).some(el => {
        return el.innerText.trim() === bookingDiv.innerText.trim();
      });

      if (duplicateExists) {
        return;
      }

      eventsContainer.appendChild(bookingDiv);
    });
  }
}

// function activateSwimmer(name) {
//   swimmerRows.forEach(row => {
//     row.classList.remove('border-primary', 'bg-light');

//     const dot = row.querySelector('.swimmer-dot');
//     if (dot) {
//       dot.classList.remove('text-success');
//       dot.classList.add('text-transparent');
//     }
//   });

//   swimmerRows.forEach(row => {
//     if (row.dataset.name === name) {
//       row.classList.add('border-primary', 'bg-light');

//       const dot = row.querySelector('.swimmer-dot');
//       if (dot) {
//         dot.classList.remove('text-transparent');
//         dot.classList.add('text-success');
//       }
//     }
//   });

//   if (studentSelect) {
//     studentSelect.value = name;
//   }

//   localStorage.setItem('activeSwimmer', name);
// }

if (tabBookings && tabCalendar) {
  tabBookings.addEventListener('click', showBookings);
  tabCalendar.addEventListener('click', showCalendar);

  if (tabBook) {
    tabBook.addEventListener('click', showBookSlot);
  }

  const savedTab = localStorage.getItem('activeTab');

  if (savedTab === 'book_slot' && tabBook) {
    showBookSlot();
  }
  else if (savedTab === 'calendar') {
    showCalendar();
  }
  else {
    showBookings();
  }
}

// swimmerRows.forEach(row => {
//   row.addEventListener('click', () => {
//     activateSwimmer(row.dataset.name);
//   });
// });

// if (studentSelect) {
//   studentSelect.addEventListener('change', function() {
//     activateSwimmer(this.value);
//   });
// }

// Do not auto-populate the swimmer field from a previous session.
// The field should remain empty when the Booking page opens.
localStorage.removeItem('activeSwimmer');

if (studentSelect) {
  studentSelect.value = '';
}

const swimmerAddForm = document.querySelector('form[action="/add_swimmer"]');
const swimmerNameInput = document.getElementById('swimmerNameInput');
const bookingForm = document.querySelector('form[action="/book"]');


