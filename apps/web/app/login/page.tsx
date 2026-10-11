"use client";

import { FormEvent, useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createSupabaseBrowserClient } from "@/lib/supabase-browser";

const highlights = [
  "Serialized component traceability",
  "Role-aware operational workspaces",
  "Audit-ready production history",
];

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage("");

    const supabase = createSupabaseBrowserClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setMessage(error.message);
      setIsSubmitting(false);
      return;
    }

    window.location.assign("/dashboard");
  }

  async function signInWithGoogle() {
    setIsSubmitting(true);
    setMessage("");

    const supabase = createSupabaseBrowserClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=/dashboard`,
      },
    });

    if (error) {
      setMessage(error.message);
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-svh bg-background lg:grid lg:grid-cols-[minmax(0,0.95fr)_minmax(480px,1.05fr)]">
      <section className="relative hidden overflow-hidden bg-[linear-gradient(145deg,#111a3a_0%,#1e2b68_48%,#3948a8_100%)] px-10 py-10 text-white lg:flex lg:flex-col xl:px-16">
        <div className="absolute -right-40 -top-40 size-[32rem] rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-48 -left-36 size-[30rem] rounded-full bg-cyan-300/10 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-white text-sm font-bold tracking-tight text-[#1e2b68] shadow-lg shadow-black/15">
            G
          </div>
          <div>
            <p className="text-sm font-semibold tracking-[0.22em] text-white/90">GOAG</p>
            <p className="text-xs text-white/55">Operations platform</p>
          </div>
        </div>

        <div className="relative my-auto max-w-xl py-20">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-medium text-white/75 backdrop-blur">
            <span className="size-1.5 rounded-full bg-emerald-300 shadow-[0_0_0_4px_rgba(110,231,183,0.12)]" />
            Built for the GOAG team
          </div>
          <h1 className="max-w-lg text-4xl font-semibold tracking-[-0.04em] text-balance xl:text-5xl">
            Build, track, and deliver with confidence.
          </h1>
          <p className="mt-6 max-w-md text-base leading-7 text-white/65">
            One clear workspace for drone manufacturing, inventory movement, and the people who keep every build moving.
          </p>

          <div className="mt-10 space-y-4">
            {highlights.map((highlight) => (
              <div key={highlight} className="flex items-center gap-3 text-sm text-white/80">
                <CheckCircle2 className="size-4 text-cyan-200" />
                {highlight}
              </div>
            ))}
          </div>
        </div>

        <div className="relative flex items-center justify-between border-t border-white/10 pt-5 text-xs text-white/45">
          <span>GOAG internal operations platform</span>
          <span>V1</span>
        </div>
      </section>

      <section className="flex min-h-svh items-center justify-center px-5 py-10 sm:px-8 lg:px-12 xl:px-20">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="grid size-10 place-items-center rounded-xl bg-primary text-sm font-bold text-primary-foreground shadow-sm">
              G
            </div>
            <div>
              <p className="text-sm font-semibold tracking-[0.22em]">GOAG</p>
              <p className="text-xs text-muted-foreground">Operations platform</p>
            </div>
          </div>

          <div className="mb-8">
            <div className="mb-5 flex size-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <ShieldCheck className="size-5" />
            </div>
            <p className="mb-2 text-sm font-medium text-primary">GOAG workspace</p>
            <h2 className="text-3xl font-semibold tracking-[-0.035em]">Welcome back</h2>
            <p className="mt-3 max-w-sm text-sm leading-6 text-muted-foreground">
              Sign in to continue to your role-specific operations workspace.
            </p>
          </div>

          <div className="space-y-6">
            <Button
              type="button"
              variant="outline"
              size="lg"
              className="h-11 w-full gap-3 bg-background font-medium"
              onClick={signInWithGoogle}
              disabled={isSubmitting}
            >
              <span className="grid size-5 place-items-center rounded-full text-sm font-bold leading-none">
                <span className="bg-[conic-gradient(from_-45deg,#4285f4_0_25%,#34a853_25%_50%,#fbbc05_50%_75%,#ea4335_75%_100%)] bg-clip-text text-transparent">
                  G
                </span>
              </span>
              {isSubmitting ? "Connecting…" : "Continue with Google"}
            </Button>

            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="h-px flex-1 bg-border" />
              <span>or continue with email</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <form onSubmit={submit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Work email</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="you@goag.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-11 pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <span className="text-xs text-muted-foreground">Authorized users only</span>
                </div>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-11 px-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-1 top-1/2 size-8 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff /> : <Eye />}
                  </Button>
                </div>
              </div>

              {message ? (
                <div id="login-error" role="alert" className="rounded-lg border border-destructive/25 bg-destructive/8 px-3 py-2.5 text-sm text-destructive">
                  {message}
                </div>
              ) : null}

              <Button type="submit" size="lg" className="h-11 w-full gap-2 font-semibold" disabled={isSubmitting}>
                {isSubmitting ? "Signing in…" : "Sign in to workspace"}
                {!isSubmitting ? <ArrowUpRight className="size-4" /> : null}
              </Button>
            </form>
          </div>

          <div className="mt-10 flex items-start gap-2.5 border-t border-border pt-5 text-xs leading-5 text-muted-foreground">
            <LockKeyhole className="mt-0.5 size-3.5 shrink-0" />
            <p>Secure access for authorized GOAG team members. Your workspace permissions are applied automatically after sign-in.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
