import { auth } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_INTERNAL_URL || "http://localhost:8000";

async function proxyToFastAPI(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const path = params.path.join("/");
  const url = `${FASTAPI_URL}/${path}`;
  const userId = (session.user as any).id;

  const headers: Record<string, string> = {
    "X-User-Id": userId,
  };

  let body: any = undefined;
  const contentType = req.headers.get("content-type") || "";

  if (req.method !== "GET" && req.method !== "HEAD") {
    if (contentType.includes("multipart/form-data")) {
      // Forward FormData (for file uploads)
      const formData = await req.formData();
      const fetchBody = new FormData();
      for (const [key, value] of formData.entries()) {
        if (value instanceof File) {
          fetchBody.append(key, value, value.name);
        } else {
          fetchBody.append(key, value);
        }
      }
      body = fetchBody;
      // Don't set Content-Type for FormData — fetch sets boundary automatically
    } else {
      headers["Content-Type"] = "application/json";
      body = await req.text();
    }
  }

  // Slow routes: PDF parsing + fund matching, or NAV history fetching.
  // upload: fund matching can take max(60, n_funds * 3) seconds — 180 s gives
  // ample headroom even for large CAS statements with 40+ funds.
  const slowRoutes = ["upload", "holdings/history", "holdings/rebuild"];
  const isSlowRoute = slowRoutes.includes(path);
  const timeoutMs = path === "upload" ? 180_000 : isSlowRoute ? 90_000 : 15_000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: req.method,
      headers,
      body,
      signal: controller.signal,
    });

    const data = await response.json();
    clearTimeout(timeoutId);
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === "AbortError") {
      const hint = path === "upload"
        ? "PDF parsing timed out — try a smaller file"
        : "Request timed out — the server is taking too long";
      return NextResponse.json({ error: hint }, { status: 504 });
    }
    console.error(`Proxy error to ${url}:`, error);
    return NextResponse.json(
      { error: "Failed to connect to internal API" },
      { status: 502 }
    );
  }
}

export async function GET(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyToFastAPI(req, context);
}

export async function POST(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyToFastAPI(req, context);
}

export async function PATCH(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyToFastAPI(req, context);
}

export async function DELETE(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyToFastAPI(req, context);
}
