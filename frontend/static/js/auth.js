const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

tabLogin.addEventListener("click", () => {
  tabLogin.classList.add("active");
  tabRegister.classList.remove("active");
  loginForm.style.display = "block";
  registerForm.style.display = "none";
});

tabRegister.addEventListener("click", () => {
  tabRegister.classList.add("active");
  tabLogin.classList.remove("active");
  registerForm.style.display = "block";
  loginForm.style.display = "none";
});

function showError(id, message) {
  const el = document.getElementById(id);
  el.textContent = message;
  el.classList.add("visible");
}
function hideError(id) {
  document.getElementById(id).classList.remove("visible");
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError("login-error");
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    await Api.post("/api/auth/login", { email, password });
    window.location.href = "/dashboard.html";
  } catch (err) {
    showError("login-error", err.message);
  }
});

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

// If already logged in, skip straight to the dashboard
Api.get("/api/auth/me").then(() => {
  window.location.href = "/dashboard.html";
}).catch(() => { /* not logged in, stay on this page */ });
