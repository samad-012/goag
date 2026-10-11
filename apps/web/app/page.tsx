import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabase-server";

export default async function HomePage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return (
      <main>
        <h1>GOAG Operations</h1>
        <p>You are not signed in.</p>
        <Link href="/login">Sign in</Link>
      </main>
    );
  }

  return (
    <main>
      <h1>GOAG Operations</h1>
      <p>Authentication session is active.</p>
      <p>Signed in as: {user.email ?? "authenticated user"}</p>
      <p>V1 technical foundation is ready for authentication and RBAC integration.</p>
      <Link href="/dashboard">Open operations dashboard</Link>
      <Link href="/logout">Sign out</Link>
    </main>
  );
}
