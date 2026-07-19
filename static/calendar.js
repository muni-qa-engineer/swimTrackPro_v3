document.addEventListener('DOMContentLoaded', function () {
    const calendarMonthInput = document.getElementById('calendarMonthInput');
    const calendarGrid = document.getElementById('calendarGrid');

    if (!calendarMonthInput || !calendarGrid) {
        return;
    }

    function renderMobileAgenda(day, dayBookings, dateKey) {
        const mobileAgendaView = document.getElementById('mobileAgendaView');
        if (!mobileAgendaView) return;

        const dateObj = new Date(calendarMonthInput.value.split('-')[0], parseInt(calendarMonthInput.value.split('-')[1]) - 1, day);
        const formattedDate = dateObj.toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' });

        let html = `<div class="agenda-title mb-2 d-flex align-items-center justify-content-between">
            <span class="fw-bold"><i class="fa-regular fa-calendar"></i> Agenda for ${formattedDate}</span>
            <span class="badge bg-info text-white rounded-pill">${dayBookings.length} Session${dayBookings.length !== 1 ? 's' : ''}</span>
        </div>`;

        if (dayBookings.length === 0) {
            html += `
                <div class="empty-state">
                    <p class="mb-0 fw-semibold text-secondary">No sessions scheduled for this day</p>
                    <small class="text-muted">Enjoy your day off!</small>
                </div>
            `;
        } else {
            dayBookings.forEach(b => {
                const approvedRequest = (b.makeupRequests || []).find(r => r.status === 'approved');
                const pendingRequest = (b.makeupRequests || []).find(r => r.status === 'pending');

                let borderClass = '';
                let statusText = '';
                let completedClass = b.completed ? 'completed' : '';

                if (b.isMakeupSession) {
                    borderClass = 'makeup';
                    statusText = '<span class="badge bg-success-subtle text-success border border-success ms-2"><i class="fa-solid fa-rotate"></i> Make-up</span>';
                } else if (approvedRequest && approvedRequest.original_date === b.sessionDate) {
                    borderClass = 'skipped';
                    statusText = '<span class="badge bg-warning-subtle text-warning border border-warning ms-2"><i class="fa-solid fa-forward-step"></i> Skipped</span>';
                    completedClass = '';
                } else if (pendingRequest && pendingRequest.original_date === b.sessionDate) {
                    borderClass = 'pending';
                    statusText = '<span class="badge bg-warning-subtle text-warning border border-warning ms-2"><i class="fa-solid fa-hourglass-half"></i> Pending Skip</span>';
                } else if (b.completed) {
                    statusText = '<span class="badge bg-secondary-subtle text-secondary border border-secondary ms-2"><i class="fa-solid fa-circle-check"></i> Completed</span>';
                }

                html += `
                    <div class="agenda-card ${borderClass} ${completedClass} calendar-session"
                        data-booking-id="${b.bookingId || ''}"
                        data-session-date="${b.sessionDate || dateKey}"
                        data-student="${b.student || ''}"
                        data-package="${b.package || ''}"
                        data-skip-remaining="${b.skipRemaining}"
                        data-valid-until="${b.validUntil}"
                        data-skip-eligible="${b.skipEligible}"
                        data-has-available-makeup-credit="${b.hasAvailableMakeupCredit}"
                        data-available-makeup-credit-id="${b.availableMakeupCreditId}"
                        data-pending-request-id="${b.pendingRequestId}"
                        data-makeup-used="${b.makeupUsed}"
                        data-session-time="${b.time}"
                    >
                        <div class="d-flex flex-column">
                            <div class="agenda-swimmer fw-bold text-dark d-flex align-items-center" style="font-size: 15px;">
                                <span>🏊</span>
                                <span class="ms-2">${b.student}</span>
                                ${statusText}
                            </div>
                            <div class="text-muted small mt-1" style="font-size: 13px;">
                                <i class="fa-regular fa-clock me-1"></i>${b.time}
                            </div>
                        </div>
                        <div>
                            <i class="fa-solid fa-chevron-right text-muted opacity-50"></i>
                        </div>
                    </div>
                `;
            });
        }

        mobileAgendaView.innerHTML = html;
    }

    function renderCalendar(year, month) {
        calendarGrid.innerHTML = '';

        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);

        const startDay = firstDay.getDay();
        const totalDays = lastDay.getDate();

        const bookings = window.bookingsData || [];

        console.log("Bookings:", bookings);

        const sessionMap = {};

        // // Debug: log all bookings loaded for the calendar
        // console.log('Calendar bookings loaded:', bookings);

        bookings.forEach(booking => {
            // New booking structure stores generated session dates in calendar_dates
            if (Array.isArray(booking.calendar_dates) && booking.calendar_dates.length > 0) {
                booking.calendar_dates.forEach(dateKey => {
                    if (!sessionMap[dateKey]) {
                        sessionMap[dateKey] = [];
                    }

                    const dateIndex = booking.calendar_dates.indexOf(dateKey);
                    const completedCount = booking.completed_classes || 0;

                    sessionMap[dateKey].push({
                        student: booking.student || booking.student_name || booking.owner_name || 'Swimmer',
                        time: booking.time || booking.session_time || '',
                        completed: dateIndex < completedCount,
                        bookingId: booking.id || '',
                        sessionDate: dateKey,
                        // Restore session metadata for Make-Up Session modal
                        package: booking.package || booking.package_name || '',
                        skipRemaining: booking.skip_remaining || 0,
                        validUntil: booking.valid_until || '',
                        skipEligible: booking.skip_eligible !== false,
                        hasAvailableMakeupCredit: booking.has_available_makeup_credit || false,
                        availableMakeupCreditId: booking.available_makeup_credit_id || '',
                        pendingRequestId: booking.pending_request_id || '',
                        makeupUsed: booking.makeup_used || false,
                        makeupRequests: booking.makeup_requests || []
                    });
                });

                return;
            }

            // Support both recurring-package bookings and generated session dates
            if (booking.session_date) {
                const dateKey = booking.session_date;

                if (!sessionMap[dateKey]) {
                    sessionMap[dateKey] = [];
                }

                sessionMap[dateKey].push({
                    student: booking.student || booking.student_name || 'Swimmer',
                    time: booking.time || booking.session_time || '',
                    bookingId: booking.id || '',
                    sessionDate: dateKey,
                    // Restore session metadata for Make-Up Session modal
                    package: booking.package || booking.package_name || '',
                    skipRemaining: booking.skip_remaining || 0,
                    validUntil: booking.valid_until || '',
                    skipEligible: booking.skip_eligible !== false,
                    hasAvailableMakeupCredit: booking.has_available_makeup_credit || false,
                    availableMakeupCreditId: booking.available_makeup_credit_id || '',
                    pendingRequestId: booking.pending_request_id || '',
                    makeupUsed: booking.makeup_used || false,
                    makeupRequests: booking.makeup_requests || []
                });

                return;
            }

            const startDate = new Date(booking.start_date);
            const endDate = new Date(booking.end_date || booking.start_date);

            const selectedDays = (booking.selected_days || '')
                .split(',')
                .map(d => d.trim().toLowerCase())
                .filter(Boolean);

            const current = new Date(startDate);

            while (current <= endDate) {
                const dayName = current.toLocaleDateString('en-US', {
                    weekday: 'long'
                }).toLowerCase();

                if (selectedDays.length === 0 || selectedDays.includes(dayName)) {
                    const dateKey = current.toISOString().split('T')[0];

                    if (!sessionMap[dateKey]) {
                        sessionMap[dateKey] = [];
                    }

                    sessionMap[dateKey].push({
                        student: booking.student || booking.student_name || 'Swimmer',
                        time: booking.time || booking.session_time || '',
                        bookingId: booking.id || '',
                        sessionDate: dateKey,
                        // Restore session metadata for Make-Up Session modal
                        package: booking.package || booking.package_name || '',
                        skipRemaining: booking.skip_remaining || 0,
                        validUntil: booking.valid_until || '',
                        skipEligible: booking.skip_eligible !== false,
                        hasAvailableMakeupCredit: booking.has_available_makeup_credit || false,
                        availableMakeupCreditId: booking.available_makeup_credit_id || '',
                        pendingRequestId: booking.pending_request_id || '',
                        makeupUsed: booking.makeup_used || false,
                        makeupRequests: booking.makeup_requests || []
                    });
                }

                current.setDate(current.getDate() + 1);
            }
        });
        // Add approved make-up sessions into the calendar
        bookings.forEach(booking => {
            (booking.makeup_requests || [])
                .filter(r => r.status === 'approved')
                .forEach(r => {
                    const targetDate = r.requested_date;

                    if (!sessionMap[targetDate]) {
                        sessionMap[targetDate] = [];
                    }

                    const exists = sessionMap[targetDate].some(s =>
                        s.bookingId === (booking.id || '') &&
                        s.sessionDate === targetDate &&
                        s.isMakeupSession
                    );

                    if (!exists) {
                        sessionMap[targetDate].push({
                            student: booking.student || booking.student_name || booking.owner_name || 'Swimmer',
                            time: booking.time || booking.session_time || '',
                            completed: false,
                            bookingId: booking.id || '',
                            sessionDate: targetDate,
                            package: booking.package || booking.package_name || '',
                            skipRemaining: booking.skip_remaining || 0,
                            validUntil: booking.valid_until || '',
                            skipEligible: false,
                            hasAvailableMakeupCredit: false,
                            availableMakeupCreditId: '',
                            pendingRequestId: '',
                            makeupUsed: true,
                            makeupRequests: booking.makeup_requests || [],
                            isMakeupSession: true,
                            originalDate: r.original_date
                        });
                    }
                });
        });
        

        for (let i = 0; i < startDay; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'col border rounded p-3';
            calendarGrid.appendChild(emptyCell);
        }

        const today = new Date();

        for (let day = 1; day <= totalDays; day++) {
            const cell = document.createElement('div');

            const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            const dayBookings = sessionMap[dateKey] || [];

            const isToday =
                day === today.getDate() &&
                month === today.getMonth() &&
                year === today.getFullYear();

            cell.className = isToday
                ? 'calendar-day-card border border-primary rounded shadow-sm p-2 bg-primary-subtle'
                : 'calendar-day-card border rounded shadow-sm bg-white p-2';

            cell.style.minHeight = '100px';

            let bookingsHtml = '';

            if (dayBookings.length > 0) {
                bookingsHtml += `
                    <div class="calendar-session-count">
                        ${dayBookings.length} Session${dayBookings.length > 1 ? 's' : ''}
                    </div>
                    <div class="calendar-bookings-container">`;

                dayBookings.forEach(b => {
                    // --- Make-Up Session Visual State ---
                    const approvedRequest = (b.makeupRequests || []).find(r => r.status === 'approved');
                    const pendingRequest = (b.makeupRequests || []).find(r => r.status === 'pending');

                    let chipClass = b.completed ? 'completed-session' : '';
                    let statusLabel = '';

                    if (b.isMakeupSession) {
                        chipClass += ' bg-success-subtle border border-success';
                        statusLabel = `
                            <span class="ms-auto" title="Make-up Session"
                                style="font-size:14px;"><i class="fa-solid fa-rotate"></i></span>
                        `;
                    }
                    else if (approvedRequest && approvedRequest.original_date === b.sessionDate) {
                        chipClass = chipClass.replace('completed-session', '');
                        chipClass += ' bg-warning-subtle border border-warning';

                        statusLabel = `
                            <span class="ms-auto" title="Skipped"
                                style="font-size:14px;"><i class="fa-solid fa-forward-step"></i></span>
                        `;
                    }
                    else if (pendingRequest && pendingRequest.original_date === b.sessionDate) {
                        chipClass += ' bg-warning-subtle border border-warning';

                        statusLabel = `
                            <span class="ms-auto" title="Approval Pending"
                                style="font-size:14px;"><i class="fa-solid fa-hourglass-half"></i></span>
                        `;
                    }

                    bookingsHtml += `
                        <div
                            class="calendar-booking-chip calendar-session ${chipClass}"
                            data-booking-id="${b.bookingId || ''}"
                            data-session-date="${b.sessionDate || dateKey}"
                            data-student="${b.student || ''}"
                            data-package="${b.package || ''}"
                            data-skip-remaining="${b.skipRemaining}"
                            data-valid-until="${b.validUntil}"
                            data-skip-eligible="${b.skipEligible}"
                            data-has-available-makeup-credit="${b.hasAvailableMakeupCredit}"
                            data-available-makeup-credit-id="${b.availableMakeupCreditId}"
                            data-pending-request-id="${b.pendingRequestId}"
                            data-makeup-used="${b.makeupUsed}"
                        >
                            <div class="d-flex align-items-center justify-content-between w-100">
                                <div class="calendar-booking-name d-flex align-items-center">
                                    <span>🏊</span>
                                    <span class="${b.completed ? 'completed-text' : ''} ms-1">
                                        ${b.student}
                                    </span>
                                </div>
                                ${statusLabel}
                            </div>
                            <div class="calendar-booking-time ${b.completed ? 'completed-text' : ''}">
                                ${b.time}
                            </div>
                        </div>`;
                });

                bookingsHtml += '</div>';
            }

            const dayLabel = new Date(year, month, day)
                .toLocaleDateString('en-US', { weekday: 'short' });

            cell.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="fw-bold text-primary" style="font-size:18px;line-height:1;">${day}</div>
                    <div class="text-muted small fw-bold ${dayLabel === 'Sat' ? 'text-warning' : dayLabel === 'Sun' ? 'text-danger' : ''}">${dayLabel}</div>
                </div>
                ${bookingsHtml}
            `;  

            calendarGrid.appendChild(cell);
        }

        // Render Mobile Date Strip
        const mobileDateStrip = document.getElementById('mobileDateStrip');
        if (mobileDateStrip) {
            mobileDateStrip.innerHTML = '';
            
            let firstActiveDay = 1;
            const todayObj = new Date();
            if (month === todayObj.getMonth() && year === todayObj.getFullYear()) {
                firstActiveDay = todayObj.getDate();
            }

            for (let day = 1; day <= totalDays; day++) {
                const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const dayBookings = sessionMap[dateKey] || [];
                const dayLabel = new Date(year, month, day).toLocaleDateString('en-US', { weekday: 'short' });

                const card = document.createElement('div');
                card.className = `date-card ${day === firstActiveDay ? 'active' : ''}`;
                card.dataset.day = day;

                let indicatorDot = '';
                if (dayBookings.length > 0) {
                    indicatorDot = '<div class="dot-indicator"></div>';
                }

                card.innerHTML = `
                    <span class="date-label">${dayLabel}</span>
                    <span class="date-num">${day}</span>
                    ${indicatorDot}
                `;

                card.addEventListener('click', function() {
                    document.querySelectorAll('.date-card').forEach(c => c.classList.remove('active'));
                    card.classList.add('active');
                    renderMobileAgenda(day, dayBookings, dateKey);
                });

                mobileDateStrip.appendChild(card);
            }

            // Render default agenda
            const defaultDateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(firstActiveDay).padStart(2, '0')}`;
            renderMobileAgenda(firstActiveDay, sessionMap[defaultDateKey] || [], defaultDateKey);

            // Auto-scroll date strip to active card
            setTimeout(() => {
                const activeCard = mobileDateStrip.querySelector('.date-card.active');
                if (activeCard) {
                    mobileDateStrip.scrollLeft = activeCard.offsetLeft - (mobileDateStrip.offsetWidth / 2) + (activeCard.offsetWidth / 2);
                }
            }, 100);
        }
    }

    const today = new Date();
    const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;

    calendarMonthInput.value = currentMonth;

    // --- Responsive view management ---
    const MOBILE_BREAKPOINT = 768; // Bootstrap md

    function isMobile() {
        return window.innerWidth < MOBILE_BREAKPOINT;
    }

    function applyCalendarLayout() {
        const gridEl = document.getElementById('calendarGrid');
        const mobileEl = document.getElementById('mobileCalendarView');
        if (!gridEl || !mobileEl) return;
        if (isMobile()) {
            gridEl.style.display = 'none';
            mobileEl.style.display = 'block';
        } else {
            gridEl.style.display = 'grid';
            mobileEl.style.display = 'none';
        }
    }

    renderCalendar(today.getFullYear(), today.getMonth());
    applyCalendarLayout();

    // Re-render on resize so mobile/desktop views stay clean
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            applyCalendarLayout();
        }, 150);
    });

    // Reopen the last edited session after redirect
    setTimeout(() => {
        if (!window.reopenBookingId || !window.reopenSessionDate) {
            return;
        }

        // On mobile view, select the correct day card first to show its agenda
        const dateParts = window.reopenSessionDate.split('-');
        if (dateParts.length === 3) {
            const reopenDay = parseInt(dateParts[2]);
            const dateCard = document.querySelector(`.date-card[data-day="${reopenDay}"]`);
            if (dateCard) {
                dateCard.click();
            }
        }

        const chip = document.querySelector(
            `.calendar-session[data-booking-id="${window.reopenBookingId}"][data-session-date="${window.reopenSessionDate}"]`
        );

        if (chip) {
            chip.click();

            // Clear values so the modal does not reopen again on future renders.
            window.reopenBookingId = '';
            window.reopenSessionDate = '';
        }
    }, 300);

    calendarMonthInput.addEventListener('change', function () {
        const [year, month] = this.value.split('-').map(Number);
        renderCalendar(year, month - 1);
        applyCalendarLayout();
    });


    // ======================================
    // V0033.0 - Monthly Calendar Session Modal
    // ======================================

  // ======================================
  // V0033.0 - Monthly Calendar Session Modal
  // ======================================

  function formatDateForDisplay(dateStr) {
    if (!dateStr || dateStr.length !== 10) return dateStr || '-';
    return dateStr.substring(8, 10) + '/' +
           dateStr.substring(5, 7) + '/' +
           dateStr.substring(0, 4);
  }

  function openCalendarSessionModal(sessionData) {
    document.getElementById('modalStudentName').textContent =
      sessionData.student || '-';

    document.getElementById('modalSessionDate').textContent =
      formatDateForDisplay(sessionData.session_date);

    document.getElementById('modalPackage').textContent =
      sessionData.package || '-';

    document.getElementById('modalSkipRemaining').textContent =
      sessionData.skip_remaining || '0';

    document.getElementById('modalValidUntil').textContent =
      sessionData.valid_until
        ? formatDateForDisplay(sessionData.valid_until)
        : '-';

    const skipForm = document.getElementById('skipSessionForm');
    const skipButton = document.getElementById('skipSessionButton');
    const undoButton = document.getElementById('undoMakeupButton');
    const proxyUndoButton =
      document.getElementById('makeupUndoProxyButton');
    const skipUndoContainer =
      document.getElementById('skipUndoContainer');
    const makeupUndoContainer =
      document.getElementById('makeupUndoContainer');

    skipForm.action =
      '/skip_session/' +
      encodeURIComponent(sessionData.booking_id) + '/' +
      encodeURIComponent(sessionData.session_date);

    const eligible = sessionData.skip_eligible !== 'false';
    // Support string and boolean values coming from dataset/JSON.
    const makeupUsed =
      sessionData.makeup_used === true ||
      sessionData.makeup_used === 'true' ||
      sessionData.makeup_used === 'True' ||
      sessionData.makeup_used === '1';

    // Reset any previous disabled styling
    skipButton.classList.remove('disabled');
    skipButton.style.pointerEvents = '';
    skipButton.style.opacity = '';

    // Completely disable the button when:
    // 1. Skip limit reached
    skipButton.disabled = !eligible;

    if (!eligible) {
      skipButton.textContent = 'Skip Limit Reached';

      // Prevent any click action at the UI level
      skipButton.classList.add('disabled');
      skipButton.style.pointerEvents = 'none';
      skipButton.style.opacity = '0.65';

    } else if (eligible) {
      
      // Enforce 6 hour rule locally for UX
      // Parse session date and time
      let sessionDateObj = new Date(sessionData.session_date);
      let sessionTimeStr = sessionData.session_time || "06:00 AM";
      let timeMatch = sessionTimeStr.match(/(\d+):(\d+)\s+(AM|PM)/i);
      
      let isTooLate = false;
      if (timeMatch) {
          let hours = parseInt(timeMatch[1], 10);
          let minutes = parseInt(timeMatch[2], 10);
          let period = timeMatch[3].toUpperCase();
          if (period === 'PM' && hours < 12) hours += 12;
          if (period === 'AM' && hours === 12) hours = 0;
          
          sessionDateObj.setHours(hours, minutes, 0, 0);
          
          let now = new Date();
          let diffHours = (sessionDateObj - now) / (1000 * 60 * 60);
          
          if (diffHours < 6) {
              isTooLate = true;
          }
      }
      
      if (isTooLate) {
          skipButton.textContent = 'Too Late to Skip';
          skipButton.classList.add('disabled');
          skipButton.style.pointerEvents = 'none';
          skipButton.style.opacity = '0.65';
      } else {
          skipButton.innerHTML = '<i class="fa-solid fa-forward-step"></i> Skip Session';
      }

    }

    // Reset undo UI state each time the modal opens.
    skipUndoContainer.style.display = 'none';
    makeupUndoContainer.style.display = 'none';

    if (undoButton) {
      undoButton.className =
        'btn btn-outline-secondary w-100';
    }

    if (proxyUndoButton) {
      proxyUndoButton.className =
        'btn btn-outline-secondary w-100';
    }

    const useMakeupForm = document.getElementById('useMakeupForm');
    const hasAvailableCredit =
      sessionData.has_available_makeup_credit === true ||
      sessionData.has_available_makeup_credit === 'true' ||
      sessionData.has_available_makeup_credit === 'True' ||
      sessionData.has_available_makeup_credit === '1';

    useMakeupForm.action = '/submit_makeup_request';

    if (
      !makeupUsed &&
      hasAvailableCredit &&
      sessionData.available_makeup_credit_id
    ) {
      document.getElementById('makeupBookingId').value =
        sessionData.booking_id;

      document.getElementById('makeupCreditId').value =
        sessionData.available_makeup_credit_id;
      document.getElementById('makeupRequestedDate').value =
        sessionData.session_date;

      const datePicker = document.getElementById('makeupDatePicker');
      const requestedDateInput =
        document.getElementById('makeupRequestedDate');

      // Restrict selectable range
    datePicker.min = sessionData.session_date;
    datePicker.max = sessionData.valid_until || '';
    datePicker.value = sessionData.session_date;

    // ---------------------------------------
    // Build blocked dates for this swimmer
    // ---------------------------------------
    const blockedDates = new Set();

    (window.bookingsData || []).forEach(booking => {

        const swimmer =
            booking.student ||
            booking.student_name ||
            booking.owner_name;

        if (swimmer !== sessionData.student) {
            return;
        }

        if (Array.isArray(booking.calendar_dates)) {
            booking.calendar_dates.forEach(date => {
                if (date !== sessionData.session_date) {
                    blockedDates.add(date);
                }
            });
        } else if (booking.session_date) {
            if (booking.session_date !== sessionData.session_date) {
                blockedDates.add(booking.session_date);
            }
        }

        // Also block approved make-up dates
        (booking.makeup_requests || [])
            .filter(r => r.status === 'approved')
            .forEach(r => {
                blockedDates.add(r.requested_date);
            });
    });

    requestedDateInput.value = datePicker.value;

    datePicker.onchange = function () {

        if (blockedDates.has(this.value)) {

            alert(
                'This swimmer already has a session on the selected date. Please choose another date.'
            );

            this.value = '';
            requestedDateInput.value = '';
            return;
        }

        requestedDateInput.value = this.value;
    };

      useMakeupForm.style.display = 'block';
    } else {
      useMakeupForm.style.display = 'none';
    }

    const trainerActions = document.getElementById('adminApprovalActions');
    // const isTrainer = {{ 'true' if role == 'trainer' else 'false' }};
    const isTrainer = window.currentUserRole === 'trainer';

    if (sessionData.pending_request_id) {
      const undoUrl =
        '/reject_makeup_request/' +
        encodeURIComponent(sessionData.pending_request_id);

      document.getElementById('undoMakeupForm').action =
        undoUrl;

      // If the make-up has already been approved and used,
      // do not allow any further actions from either guest or admin.
      if (makeupUsed) {
        skipButton.disabled = true;
        skipButton.textContent = 'Make-Up Already Used';
        skipButton.classList.add('disabled');
        skipButton.style.pointerEvents = 'none';
        skipButton.style.opacity = '0.65';

        // Hide request/undo actions because the workflow is complete.
        useMakeupForm.style.display = 'none';
        makeupUndoContainer.style.display = 'none';
        trainerActions.style.display = 'none';

      } else {
        // Pending request: allow undo and admin approval.
        makeupUndoContainer.style.display = 'block';

        if (proxyUndoButton) {
          proxyUndoButton.className =
            'btn btn-secondary w-100';
        }

        if (isTrainer) {
          document.getElementById('approveMakeupForm').action =
            '/approve_makeup_request/' +
            encodeURIComponent(sessionData.pending_request_id);

          document.getElementById('rejectMakeupForm').action =
            undoUrl;

          trainerActions.style.display = 'block';
        } else {
          trainerActions.style.display = 'none';
        }
      }
    } else if (
      hasAvailableCredit &&
      sessionData.available_makeup_credit_id &&
      !makeupUsed
    ) {
      const undoUrl =
        '/undo_skip_session/' +
        encodeURIComponent(sessionData.booking_id) + '/' +
        encodeURIComponent(sessionData.session_date);

      document.getElementById('undoMakeupForm').action =
        undoUrl;

      // Show Undo beside "Skip Session" and highlight it.
      // Since a skip credit already exists for this date, the user
      // must not be able to skip the same session again.
      skipUndoContainer.style.display = 'block';

      // Disable the Skip button completely.
      skipButton.disabled = true;
      skipButton.textContent = 'Already Skipped';
      skipButton.classList.add('disabled');
      skipButton.style.pointerEvents = 'none';
      skipButton.style.opacity = '0.65';

      if (undoButton) {
        undoButton.className =
          'btn btn-secondary w-100';
      }

      trainerActions.style.display = 'none';

    } else {
      trainerActions.style.display = 'none';
    }

    const modalElement = document.getElementById('sessionOptionsModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
  }
  document.addEventListener('click', function(event) {
    const sessionEl = event.target.closest('.calendar-session');
    if (!sessionEl) return;

    event.preventDefault();

    openCalendarSessionModal({
      booking_id: sessionEl.dataset.bookingId,
      student: sessionEl.dataset.student,
      package: sessionEl.dataset.package,
      session_date: sessionEl.dataset.sessionDate,
      session_time: sessionEl.dataset.sessionTime,
      skip_remaining: sessionEl.dataset.skipRemaining,
      valid_until: sessionEl.dataset.validUntil,
      skip_eligible: sessionEl.dataset.skipEligible,
      has_available_makeup_credit:
        sessionEl.dataset.hasAvailableMakeupCredit,
      available_makeup_credit_id:
        sessionEl.dataset.availableMakeupCreditId,
      pending_request_id:
        sessionEl.dataset.pendingRequestId,
      makeup_used:
        sessionEl.dataset.makeupUsed ||
        (sessionEl.textContent.includes('Approved') ? 'true' : 'false')
    });
  });

  // Calendar modal actions
  if (typeof enableFormLoading === 'function') {
    enableFormLoading('skipSessionForm', 'Processing...');
    enableFormLoading('useMakeupForm', 'Submitting...');
    enableFormLoading('approveMakeupForm', 'Approving...');
    enableFormLoading('rejectMakeupForm', 'Rejecting...');
    enableFormLoading('undoMakeupForm', 'Undoing...');
  }
});