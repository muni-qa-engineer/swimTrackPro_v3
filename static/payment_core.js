function updatePaymentSummary() {
  const bookings = window.bookingsData || [];

  let paidAmount = 0;
  let pendingAmount = 0;
  let notPaidAmount = 0;

  bookings.forEach(booking => {
    const amount = Number(booking.fee || 0);
    const status = String(booking.status || '').trim().toLowerCase();

    if (status === 'paid') {
      paidAmount += amount;
    }
    else if (status === 'pending' || status === 'pending verification') {
      pendingAmount += amount;
    }
    else {
      notPaidAmount += amount;
    }
  });

  const paidCard = document.getElementById('paidAmountCard');
  const pendingCard = document.getElementById('pendingAmountCard');
  const notPaidCard = document.getElementById('notPaidAmountCard');

  if (paidCard) paidCard.innerHTML = `<i class="fa-solid fa-indian-rupee-sign"></i>${paidAmount.toLocaleString()}`;
  if (pendingCard) pendingCard.innerHTML = `<i class="fa-solid fa-indian-rupee-sign"></i>${pendingAmount.toLocaleString()}`;
  if (notPaidCard) notPaidCard.innerHTML = `<i class="fa-solid fa-indian-rupee-sign"></i>${notPaidAmount.toLocaleString()}`;
}

function updatePaymentTable() {
  const bookings = window.bookingsData || [];
  const currentRole = window.currentUserRole || '';
  const tableBody = document.getElementById('paymentTableBody');

  if (!tableBody) return;

  if (bookings.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center text-muted py-4" style="color: var(--color-text-muted) !important;">
          No payment records found.
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = bookings.map(booking => {
    const owner = booking.owner || booking.created_by || '-';
    const swimmer = booking.student || '-';
    const packageName = booking.package || '-';
    const status = booking.status || 'Not Paid';
    const amount = Number(booking.fee || 0).toLocaleString();
    const isTrainer = currentRole === 'trainer';
    const isPendingVerification = status === 'Pending Verification';
    const isPaid = status === 'Paid';

    return `
      <tr>
        <td style="color: white; font-weight: 600;">${owner}</td>
        <td>${swimmer}</td>
        <td>${packageName}</td>
        <td>
          ${isTrainer ? `
            ${isPendingVerification ? `
              <div class="flex gap-2">
                <button type="button" class="btn btn-primary btn-sm payment-status-action-btn" data-booking-id="${booking.id || ''}" data-status="Paid" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; border-radius: var(--radius-sm);">
                  <i class="fa-solid fa-circle-check"></i> Verify
                </button>
                <button type="button" class="btn btn-outline btn-sm payment-status-action-btn" data-booking-id="${booking.id || ''}" data-status="Not Paid" style="border-color: var(--color-danger); color: var(--color-danger); padding: 0.35rem 0.75rem; font-size: 0.8rem; border-radius: var(--radius-sm);">
                  <i class="fa-solid fa-circle-xmark"></i> Reject
                </button>
              </div>
            ` : `
              <span class="badge ${isPaid ? 'badge-success' : 'badge-danger'}">
                ${status}
              </span>
            `}
          ` : `
            ${isPaid ? `
              <span class="badge badge-success">Paid</span>
            ` : isPendingVerification ? `
              <span class="badge badge-warning">Pending Verification</span>
            ` : `
              <select class="form-select form-select-sm payment-status-select" data-booking-id="${booking.id || ''}" style="background: rgba(0,0,0,0.4); color: white; border: 1px solid rgba(255,255,255,0.1); width: 150px; font-size: 0.8rem;">
                <option value="Not Paid" ${status === 'Not Paid' ? 'selected' : ''}>Not Paid</option>
                <option value="Paid">Mark as Paid</option>
              </select>
            `}
          `}
        </td>
        <td>₹${amount}</td>
        <td>
          ${isTrainer ? `
            ${isPendingVerification ? 'Awaiting Decision' : 'Verified'}
          ` : `
            ${isPaid ? `
              <span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Verified</span>
            ` : isPendingVerification ? `
              <span class="badge badge-warning"><i class="fa-solid fa-hourglass-half"></i> Pending</span>
            ` : `
              <a href="upi://pay?pa=${window.upiId || ''}&pn=${encodeURIComponent(window.accountHolderName || '')}&am=${booking.fee || 0}&cu=INR&tn=SwimTrackPro%20Payment"
                class="btn btn-primary btn-sm" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;"
                title="Open UPI App">
                <i class="fa-solid fa-credit-card"></i> Pay Now (₹${booking.fee || 0})
              </a>
            `}
          `}
        </td>
      </tr>
    `;
  }).join('');
  
  // Re-bind actions since table was populated
  initializePaymentStatusActions();
}

function initializePaymentStatusActions() {
  // Trainer action buttons for verifying/rejecting payment
  const trainerButtons = document.querySelectorAll('.payment-status-action-btn');
  trainerButtons.forEach(button => {
    button.addEventListener('click', async function() {
      const bookingId = this.dataset.bookingId;
      const selectedStatus = this.dataset.status;
      this.disabled = true;
      this.textContent = 'Processing...';

      try {
        const formData = new FormData();
        formData.append('status', selectedStatus);

        const response = await fetch(`/update_payment_status/${bookingId}`, {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          window.location.reload();
        } else {
          throw new Error('Update failed');
        }
      } catch (error) {
        alert('Failed to update payment status');
        this.disabled = false;
        this.innerHTML = 'Retry';
      }
    });
  });

  // Swimmer status select dropdown change
  const selectDropdowns = document.querySelectorAll('.payment-status-select');
  selectDropdowns.forEach(select => {
    select.addEventListener('change', async function() {
      const bookingId = this.dataset.bookingId;
      const selectedStatus = this.value;
      
      if (selectedStatus === 'Paid') {
        const confirmChange = confirm('Have you successfully paid for this booking? Changing this status will alert the coach/admin for verification.');
        if (!confirmChange) {
          this.value = 'Not Paid';
          return;
        }
      }

      this.disabled = true;

      try {
        const formData = new FormData();
        formData.append('status', selectedStatus);

        const response = await fetch(`/update_payment_status/${bookingId}`, {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          window.location.reload();
        } else {
          throw new Error('Update failed');
        }
      } catch (error) {
        alert('Failed to update payment status');
        this.disabled = false;
        this.value = 'Not Paid';
      }
    });
  });
}
