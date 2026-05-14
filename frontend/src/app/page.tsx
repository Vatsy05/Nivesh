import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";

export default async function HomePage() {
  try {
    const session = await auth();
    if (session) {
      redirect("/dashboard/upload");
    } else {
      redirect("/auth/login");
    }
  } catch {
    // If auth() throws for any reason (missing env, DB issue, etc.)
    // always fall back to the login page so the user isn't stuck.
    redirect("/auth/login");
  }
}
