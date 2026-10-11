export type CurrentUserResponse = {
  user: {
    id: string;
    email: string;
    display_name: string;
    status: string;
  };
  membership: {
    id: string;
    company_id: string;
    status: string;
  };
  role_codes: string[];
  permission_codes: string[];
};

export class ApiClientError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

export function createApiClient(accessToken: string) {
  const baseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace("localhost", "127.0.0.1");

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
        ...init?.headers,
      },
    });

    if (!response.ok) {
      let message = `API request failed with status ${response.status}`;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // Keep the status-based message when the API response is not JSON.
      }
      throw new ApiClientError(response.status, message);
    }

    return (await response.json()) as T;
  }

  return {
    getCurrentUser: () => request<CurrentUserResponse>("/me"),
  };
}
