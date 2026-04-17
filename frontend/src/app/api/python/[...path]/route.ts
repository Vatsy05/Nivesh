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

  try {
    const response = await fetch(url, {
      method: req.method,
      headers,
      body,
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
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
