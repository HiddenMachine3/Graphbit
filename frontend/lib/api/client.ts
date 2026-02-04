export type ApiError = {
  message: string;
  status?: number;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  return JSON.parse(text) as T;
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const data = await parseJson<{ message?: string }>(response);
      if (data?.message) {
        message = data.message;
      }
    } catch {
      // ignore parse errors
    }
    const error: ApiError = { message, status: response.status };
    throw error;
  }

  return parseJson<T>(response);
}
