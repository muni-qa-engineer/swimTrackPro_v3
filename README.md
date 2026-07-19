# 🏊 SwimTrackPro

**SwimTrackPro** is a comprehensive, full-stack web and mobile application designed to streamline the operations of swimming academies. Built with **Flask** and **PostgreSQL**, it serves as a centralized platform for managing class schedules, handling user bookings, tracking payments, and facilitating seamless communication between coaches and students.

With a fully responsive, modern glassmorphism UI, SwimTrackPro is also configured as a **Progressive Web App (PWA)**, allowing users and trainers to install it directly to their iOS or Android home screens for a native app experience.

---

## ✨ Key Features

### 👥 Multi-Role Architecture
- **Super Admin**: Complete oversight of the system. Approve new trainers, manage all bookings, monitor global payments, and control the global Notice Board.
- **Trainer/Coach**: Dedicated dashboard to view daily schedules, manage swimmer attendance, update their professional profile (with an integrated photo album), and securely reset passwords via OTP.
- **Guest/User**: Intuitive portal to book swimming packages, request class pauses, track make-up class credits, and view payment histories.

### 📱 Progressive Web App (PWA)
- **Installable**: Users can install SwimTrackPro directly to their mobile devices from the browser.
- **Offline Resiliency**: Built-in Service Workers cache core UI assets for near-instant load times on mobile networks.
- **App-Like Feel**: Standalone display mode hides browser chrome, providing a true native feel.

### 🛡️ Security & Authentication
- **Role-Based Access Control (RBAC)**: Distinct login flows and session management for Admins, Trainers, and Guests.
- **OTP Verification**: Forgot password workflows for Trainers are secured via 6-digit OTPs sent directly to their email, powered by the **Brevo API**. OTPs are securely stored in the database with strict 10-minute expiry windows.

### 📅 Advanced Booking & Class Management
- **Make-Up Classes**: Automated system for tracking missed classes and issuing Make-Up credits.
- **Package Pausing**: Users can request to pause their active packages, which are logged into a comprehensive audit trail for Admin approval.
- **Dynamic Dashboards**: Real-time stat cards, dynamic schedule loading, and beautiful animated UI components.

---

## 🛠️ Technology Stack

- **Backend**: Python, Flask, Psycopg2
- **Database**: PostgreSQL
- **Frontend**: HTML5, Vanilla CSS (Glassmorphism UI), JavaScript (ES6), Bootstrap 5
- **Email Delivery**: Brevo API
- **Architecture**: Progressive Web App (PWA)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Brevo API Key (for email services)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/swimtrackpro.git
   cd swimtrackpro
   ```

2. **Set up a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the Database**
   - Ensure your local PostgreSQL server is running.
   - Create a new database for the application.
   - The tables (e.g., `trainers`, `bookings`, `password_reset_otps`) will be automatically initialized when the app runs.

5. **Environment Variables**
   Update your `config.py` with your specific credentials:
   ```python
   DATABASE_URL = "postgresql://user:password@localhost/dbname"
   SECRET_KEY = "your_secure_secret_key"
   BREVO_API_KEY = "your_brevo_api_key"
   ```

6. **Run the Application**
   ```bash
   python3 app.py
   ```
   The application will be available at `http://127.0.0.1:5000/`.

---

## 📱 Mobile Installation (PWA)

To test the mobile app experience on your phone:
1. Ensure your phone and development machine are on the same network, and access the app via your machine's local IP address.
2. **iOS Safari**: Tap the "Share" icon at the bottom and select "Add to Home Screen".
3. **Android Chrome**: Tap the "Install App" prompt at the bottom of the screen, or select it from the 3-dot menu.

---

## 📄 License
© 2026 Swimming Summer Camp. All rights reserved.