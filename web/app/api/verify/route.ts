import { NextRequest, NextResponse } from "next/server";

// Proxy to the backend's offline receipt verifier (same token handling as /api/ask).
export const dynamic = "force-dynamic";

const API_URL = process.env.TESSERA_API_URL ?? "http://127.0.0.1:8080";
const API_TOKEN = process.env.TESSERA_API_TOKEN;

export async function POST(req: NextRequest) {
  const body = await req.json();
  try {
    const res = await fetch(`${API_URL}/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : {}),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json({ detail: `backend unreachable: ${String(e)}` }, { status: 502 });
  }
}
