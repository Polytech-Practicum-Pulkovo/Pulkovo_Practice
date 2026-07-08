export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(baseUrl, path, options = {}) {
  const { params, ...init } = options;
  let url = `${baseUrl}${path}`;

  if (params) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        search.append(key, value);
      }
    });
    const qs = search.toString();
    if (qs) url += `?${qs}`;
  }

  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

export function get(baseUrl, path, params) {
  return request(baseUrl, path, { method: "GET", params });
}

export function post(baseUrl, path, body) {
  return request(baseUrl, path, { method: "POST", body: JSON.stringify(body ?? {}) });
}

export function put(baseUrl, path, body) {
  return request(baseUrl, path, { method: "PUT", body: JSON.stringify(body ?? {}) });
}

export function del(baseUrl, path, params) {
  return request(baseUrl, path, { method: "DELETE", params });
}
