/* Thin wrapper around fetch() for the JSON API. Cookies (httponly session)
   are sent automatically via credentials: 'include'. */

const Api = {
  async request(method, path, { body, isForm } = {}) {
    const opts = {
      method,
      credentials: "include",
      headers: {},
    };
    if (body !== undefined) {
      if (isForm) {
        opts.body = body; // FormData - browser sets content-type
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }

    const res = await fetch(path, opts);

    if (res.status === 401) {
      if (!path.includes("/api/auth/")) {
        window.location.href = "/index.html";
      }
    }

    let data = null;
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await res.json().catch(() => null);
    }

    if (!res.ok) {
      const message = (data && data.detail) || `Request failed (${res.status})`;
      throw new Error(typeof message === "string" ? message : "Request failed.");
    }
    return data;
  },

  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, { body }); },
  put(path, body) { return this.request("PUT", path, { body }); },
  del(path) { return this.request("DELETE", path); },
  postForm(path, formData) { return this.request("POST", path, { body: formData, isForm: true }); },
};

async function requireAuth() {
  try {
    return await Api.get("/api/auth/me");
  } catch (e) {
    window.location.href = "/index.html";
    return null;
  }
}
