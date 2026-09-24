// DOM Elements
const authTabs = document.getElementById("auth-tabs");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const forgotSection = document.getElementById("forgot-section");
const forgotForm = document.getElementById("forgot-form");
const verifySection = document.getElementById("verify-section");
const verifyForm = document.getElementById("verify-form");
const resetSection = document.getElementById("reset-section");
const resetForm = document.getElementById("reset-form");

const linkForgotPassword = document.getElementById("link-forgot-password");
const btnSendOtp = document.getElementById("btn-send-otp");
const btnVerifyOtp = document.getElementById("btn-verify-otp");
const btnResendOtp = document.getElementById("btn-resend-otp");
const btnResetPassword = document.getElementById("btn-reset-password");

const timerCountdown = document.getElementById("timer-countdown");
const timerWrap = document.getElementById("otp-timer-wrap");

// State
let resetEmail = "";
let resetToken = "";
let otpCountdownInterval = null;
let resendCooldownInterval = null;

// Error & Success display helpers
function showError(id, message) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.classList.add("visible");
}

function hideError(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("visible");
}

function showSuccess(id, message) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.classList.add("visible");
}

function hideSuccess(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("visible");
}

function clearAllFeedback() {
  [
    "login-error", "login-success",
    "register-error",
    "forgot-error", "forgot-success",
    "verify-error", "verify-success",
    "reset-error", "reset-success"
  ].forEach(id => {
    hideError(id);
    hideSuccess(id);
  });
}

function stopTimers() {
  if (otpCountdownInterval) {
    clearInterval(otpCountdownInterval);
    otpCountdownInterval = null;
  }
  if (resendCooldownInterval) {
    clearInterval(resendCooldownInterval);
    resendCooldownInterval = null;
  }
}

// View switcher
function showLoginView(successMessage = null) {
  stopTimers();
  clearAllFeedback();

  authTabs.style.display = "flex";
  tabLogin.classList.add("active");
  tabRegister.classList.remove("active");

  loginForm.style.display = "block";
  registerForm.style.display = "none";
  forgotSection.style.display = "none";
  verifySection.style.display = "none";
  resetSection.style.display = "none";

  if (successMessage) {
    showSuccess("login-success", successMessage);
  }
}

function showRegisterView() {
  stopTimers();
  clearAllFeedback();

  authTabs.style.display = "flex";
  tabRegister.classList.add("active");
  tabLogin.classList.remove("active");

  registerForm.style.display = "block";
  loginForm.style.display = "none";
  forgotSection.style.display = "none";
  verifySection.style.display = "none";
  resetSection.style.display = "none";
}

function showForgotView() {
  stopTimers();
  clearAllFeedback();

  authTabs.style.display = "none";
  loginForm.style.display = "none";
  registerForm.style.display = "none";
  verifySection.style.display = "none";
  resetSection.style.display = "none";
  forgotSection.style.display = "block";

  const loginEmailVal = document.getElementById("login-email").value.trim();
  const forgotEmailInput = document.getElementById("forgot-email");
  if (loginEmailVal) {
    forgotEmailInput.value = loginEmailVal;
  }
  forgotEmailInput.focus();
}

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function startOtpTimer(durationSeconds = 600) {
  if (otpCountdownInterval) clearInterval(otpCountdownInterval);
  let remaining = durationSeconds;
  timerCountdown.textContent = formatTime(remaining);
  timerWrap.classList.remove("expired");

  otpCountdownInterval = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(otpCountdownInterval);
      otpCountdownInterval = null;
      timerCountdown.textContent = "00:00";
      timerWrap.classList.add("expired");
      showError("verify-error", "OTP has expired. Please request a new one.");
    } else {
      timerCountdown.textContent = formatTime(remaining);
    }
  }, 1000);
}

function startResendCooldown(cooldownSeconds = 60) {
  if (resendCooldownInterval) clearInterval(resendCooldownInterval);
  let remaining = cooldownSeconds;
  btnResendOtp.disabled = true;
  btnResendOtp.textContent = `Resend OTP (${remaining}s)`;

  resendCooldownInterval = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(resendCooldownInterval);
      resendCooldownInterval = null;
      btnResendOtp.disabled = false;
      btnResendOtp.textContent = "Resend OTP";
    } else {
      btnResendOtp.textContent = `Resend OTP (${remaining}s)`;
    }
  }, 1000);
}

function showVerifyView(initialNotice = null) {
  clearAllFeedback();

  authTabs.style.display = "none";
  loginForm.style.display = "none";
  registerForm.style.display = "none";
  forgotSection.style.display = "none";
  resetSection.style.display = "none";
  verifySection.style.display = "block";

  const otpInput = document.getElementById("otp-input");
  otpInput.value = "";
  otpInput.focus();

  if (initialNotice) {
    showSuccess("verify-success", initialNotice);
  }

  startOtpTimer(600);
  startResendCooldown(60);
}

function showResetView() {
  stopTimers();
  clearAllFeedback();

  authTabs.style.display = "none";
  loginForm.style.display = "none";
  registerForm.style.display = "none";
  forgotSection.style.display = "none";
  verifySection.style.display = "none";
  resetSection.style.display = "block";

  document.getElementById("new-password").value = "";
  document.getElementById("confirm-password").value = "";
  document.getElementById("new-password").focus();
}

// Navigation event listeners
tabLogin.addEventListener("click", () => showLoginView());
tabRegister.addEventListener("click", () => showRegisterView());

if (linkForgotPassword) {
  linkForgotPassword.addEventListener("click", (e) => {
    e.preventDefault();
    showForgotView();
  });
}

document.querySelectorAll(".back-to-login").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    showLoginView();
  });
});

// 1. Login Form Submit
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("login-error");
  hideSuccess("login-success");
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    await Api.post("/api/auth/login", { email, password });
    window.location.href = "/dashboard.html";
  } catch (err) {
    showError("login-error", err.message);
  }
});

// 2. Register Form Submit
registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("register-error");
  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  try {
    await Api.post("/api/auth/register", { name, email, password });
    window.location.href = "/dashboard.html";
  } catch (err) {
    showError("register-error", err.message);
  }
});

// 3. Forgot Password Form Submit (Send OTP)
forgotForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("forgot-error");
  hideSuccess("forgot-success");

  const email = document.getElementById("forgot-email").value.trim();
  if (!email) return;

  btnSendOtp.disabled = true;
  btnSendOtp.textContent = "Sending OTP...";

  try {
    const res = await Api.post("/api/auth/forgot-password", { email });
    resetEmail = email;
    showVerifyView(res.message || "If an account exists for this email, a password reset OTP has been sent.");
  } catch (err) {
    showError("forgot-error", err.message);
  } finally {
    btnSendOtp.disabled = false;
    btnSendOtp.textContent = "Send OTP";
  }
});

// 4. Resend OTP Button Click
btnResendOtp.addEventListener("click", async () => {
  if (btnResendOtp.disabled) return;
  hideError("verify-error");
  hideSuccess("verify-success");

  btnResendOtp.disabled = true;
  btnResendOtp.textContent = "Sending...";

  try {
    const res = await Api.post("/api/auth/resend-otp", { email: resetEmail });
    showSuccess("verify-success", res.message || "A new OTP has been sent to your email.");
    startOtpTimer(600);
    startResendCooldown(60);
  } catch (err) {
    showError("verify-error", err.message);
    btnResendOtp.disabled = false;
    btnResendOtp.textContent = "Resend OTP";
  }
});

// 5. Verify OTP Form Submit
verifyForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("verify-error");
  hideSuccess("verify-success");

  const otp = document.getElementById("otp-input").value.trim();
  if (!otp || otp.length !== 6 || !/^\d{6}$/.test(otp)) {
    showError("verify-error", "Please enter a valid 6-digit OTP.");
    return;
  }

  btnVerifyOtp.disabled = true;
  btnVerifyOtp.textContent = "Verifying...";

  try {
    const res = await Api.post("/api/auth/verify-otp", { email: resetEmail, otp });
    resetToken = res.reset_token;
    showResetView();
  } catch (err) {
    showError("verify-error", err.message);
  } finally {
    btnVerifyOtp.disabled = false;
    btnVerifyOtp.textContent = "Verify OTP";
  }
});

// 6. Reset Password Form Submit
resetForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("reset-error");
  hideSuccess("reset-success");

  const newPassword = document.getElementById("new-password").value;
  const confirmPassword = document.getElementById("confirm-password").value;

  if (newPassword !== confirmPassword) {
    showError("reset-error", "Passwords do not match.");
    return;
  }

  if (newPassword.length < 8) {
    showError("reset-error", "Password must be at least 8 characters long.");
    return;
  }
  if (!/[A-Za-z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
    showError("reset-error", "Password must contain both letters and numbers.");
    return;
  }

  btnResetPassword.disabled = true;
  btnResetPassword.textContent = "Resetting Password...";

  try {
    const res = await Api.post("/api/auth/reset-password", {
      email: resetEmail,
      reset_token: resetToken,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });

    const successMsg = res.message || "Password reset successfully. Please log in with your new password.";
    showLoginView(successMsg);
    document.getElementById("login-email").value = resetEmail;
    document.getElementById("login-password").value = "";
    document.getElementById("login-password").focus();
  } catch (err) {
    showError("reset-error", err.message);
  } finally {
    btnResetPassword.disabled = false;
    btnResetPassword.textContent = "Reset Password";
  }
});

// If already logged in, skip straight to the dashboard
Api.get("/api/auth/me").then(() => {
  window.location.href = "/dashboard.html";
}).catch(() => { /* not logged in, stay on this page */ });
