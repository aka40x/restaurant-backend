// File dung chung cho ca nhom: moi lan goi API deu di qua day.
const API_BASE_URL = "http://127.0.0.1:8000";

function getToken() {
    return localStorage.getItem("token");
}

function setToken(token) {
    localStorage.setItem("token", token);
}

function clearToken() {
    localStorage.removeItem("token");
}

async function apiRequest(path, method = "GET", body = null, auth = false) {
    const headers = { "Content-Type": "application/json" };
    if (auth && getToken()) {
        headers["Authorization"] = "Bearer " + getToken();
    }

    const options = { method: method, headers: headers };
    if (body !== null) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(API_BASE_URL + path, options);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.message || "Request failed");
    }
    return result;
}
