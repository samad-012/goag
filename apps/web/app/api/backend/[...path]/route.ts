import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase-server";

type RouteContext = { params: Promise<{ path: string[] }> };
const UPSTREAM_TIMEOUT_MS = 10_000;

async function proxy(request: NextRequest, context: RouteContext) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  }

  const { path } = await context.params;
  const baseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace("localhost", "127.0.0.1");
  const target = `${baseUrl}/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);
  headers.set("Accept", "application/json");
  headers.delete("host");

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: controller.signal,
    });
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === "AbortError";
    return NextResponse.json(
      { detail: timedOut ? "The backend service timed out. Please retry." : "The backend service is unavailable. Please retry." },
      { status: timedOut ? 504 : 502 },
    );
  } finally {
    clearTimeout(timeoutId);
  }

  const responseBody = await response.arrayBuffer();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
