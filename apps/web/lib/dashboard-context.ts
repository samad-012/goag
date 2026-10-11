import { redirect } from "next/navigation";
import { createApiClient, type CurrentUserResponse } from "@/lib/api-client";
import { createSupabaseServerClient } from "@/lib/supabase-server";

export async function getDashboardContext(): Promise<{
  email: string;
  currentUser: CurrentUserResponse | null;
  apiError: string;
}> {
  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    return { email: user.email ?? "authenticated user", currentUser: null, apiError: "Your authentication session is unavailable. Please sign in again." };
  }

  try {
    return { email: user.email ?? "authenticated user", currentUser: await createApiClient(session.access_token).getCurrentUser(), apiError: "" };
  } catch (error) {
    return { email: user.email ?? "authenticated user", currentUser: null, apiError: error instanceof Error ? error.message : "Unable to load your GOAG profile." };
  }
}
