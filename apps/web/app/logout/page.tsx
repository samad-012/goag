"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createSupabaseBrowserClient } from "@/lib/supabase-browser";

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    createSupabaseBrowserClient().auth.signOut().finally(() => router.replace("/login"));
  }, [router]);

  return <p>Signing out…</p>;
}
