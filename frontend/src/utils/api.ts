// frontend/src/utils/api.ts
const API_BASE = import.meta.env.DEV
  ? "/api/v1"
  : "https://your-production-url.com/api/v1";

// API is expensive.
const MOCK_DIAGNOSES = [
  "One reading of your situation: We believe your core problem is customer awareness — people in the settlement don't know your product exists. If this is correct, you should see that people who do try your chapati tend to come back, but new customers are rare. Your priority should be visibility, not product changes.",
  "A different reading: We see a different pattern. Your core problem is perceived value relative to price — customers know about you but choose cheaper alternatives. If this is correct, you should see that customers visit but don't buy, or buy once but switch. Your priority should be either reducing costs or increasing perceived quality.",
  "A third possibility: We disagree with both readings. Your core problem is inconsistent quality — you sometimes deliver a good product but can't do it reliably. If this is correct, you should see that some days sell well and others don't, and repeat customers are unpredictable. Your priority should be standardizing your production process.",
];

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  // FIXME: mock here
  if (endpoint.endsWith("/generate-diagnosis") && import.meta.env.DEV) {
    // Pretending that we're working hard.
    await new Promise((resolve) => setTimeout(resolve, 1000));

    return {
      type: "competing",
      diagnoses: MOCK_DIAGNOSES,
      labels: [
        "One reading of your situation:",
        "A different reading:",
        "A third possibility:",
      ],
      response_prompt:
        "Based on what you've read and your own experience, how do you now understand the core challenge your venture is facing?",
    } as unknown as T;
  }

  if (endpoint.endsWith("/selection") && import.meta.env.DEV) {
    return { status: "ok" } as unknown as T;
  }

  if (endpoint.endsWith("/response") && import.meta.env.DEV) {
    await new Promise((resolve) => setTimeout(resolve, 800));
    return { status: "ok", next: "survey" } as unknown as T;
  }

  if (endpoint.endsWith("/survey") && import.meta.env.DEV) {
    await new Promise((resolve) => setTimeout(resolve, 800));
    return { status: "complete" } as unknown as T;
  }

  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP Error: ${response.status}`);
  }

  return response.json();
}
