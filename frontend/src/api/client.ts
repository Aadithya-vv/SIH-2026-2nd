export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? data.detail
              .map(
                (issue: { loc?: string[]; msg?: string }) =>
                  `${issue.loc?.join(".") ?? "Input"}: ${issue.msg ?? "Invalid value"}`,
              )
              .join("; ")
          : `Request failed (${response.status}). Check the submitted fields.`,
    );
  }
  return response.json();
}
