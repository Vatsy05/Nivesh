import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Protect all /dashboard routes
  if (pathname.startsWith("/dashboard")) {
    if (!req.auth) {
      const loginUrl = new URL("/auth/login", req.nextUrl.origin);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect authenticated users away from auth pages
  if (pathname.startsWith("/auth/")) {
    if (req.auth) {
      return NextResponse.redirect(new URL("/dashboard/upload", req.nextUrl.origin));
    }
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/dashboard/:path*", "/auth/:path*"],
};
