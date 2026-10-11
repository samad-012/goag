"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { WORKSPACE_REFRESH_EVENT } from "@/lib/workspace-events";

type MailboxStatus = {
  configured: boolean;
  connected: boolean;
  provider: string;
  mailbox_email: string | null;
  message: string;
};

type MailboxMessage = {
  id: string;
  thread_id: string | null;
  sender: string;
  recipients: string;
  subject: string;
  snippet: string;
  received_at: string | null;
  label_ids: string[];
  unread: boolean;
};

type MailboxThreadMessage = {
  id: string;
  thread_id: string | null;
  sender: string;
  recipients: string;
  subject: string;
  body: string;
  sent_at: string | null;
  label_ids: string[];
};

async function emailRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

export function EmailPanel({ permissions }: { permissions: string[] }) {
  const canRead = permissions.includes("mailbox.read");
  const canManage = permissions.includes("mailbox.manage");
  const canSend = permissions.includes("mailbox.send");
  const [status, setStatus] = useState<MailboxStatus | null>(null);
  const [error, setError] = useState("");
  const [inboxError, setInboxError] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [messages, setMessages] = useState<MailboxMessage[]>([]);
  const [selectedThread, setSelectedThread] = useState<MailboxThreadMessage[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [sendResult, setSendResult] = useState("");
  const [sending, setSending] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [subject, setSubject] = useState("GOAG mailbox connection test");
  const [body, setBody] = useState(
    "This is a test email from the connected GOAG mailbox. The email connection is working.",
  );

  useEffect(() => {
    if (!canRead) return;
    void emailRequest<MailboxStatus>("/email/status")
      .then(setStatus)
      .catch((loadError) =>
        setError(loadError instanceof Error ? loadError.message : "Unable to load mailbox status."),
      );
  }, [canRead]);

  async function loadMessages(query = activeQuery) {
    setLoadingMessages(true);
    setInboxError("");
    try {
      const params = new URLSearchParams({ max_results: "25" });
      if (query.trim()) params.set("q", query.trim());
      const result = await emailRequest<{ messages: MailboxMessage[] }>(`/email/messages?${params}`);
      setMessages(result.messages);
      setSelectedThread([]);
    } catch (loadError) {
      setInboxError(loadError instanceof Error ? loadError.message : "Unable to load messages.");
    } finally {
      setLoadingMessages(false);
    }
  }

  useEffect(() => {
    if (!status?.connected) return;
    void loadMessages();
    // The connected state is the only trigger needed for the initial inbox load.
    // Search and refresh call loadMessages directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.connected]);

  useEffect(() => {
    const refresh = () => {
      if (!canRead) return;
      void emailRequest<MailboxStatus>("/email/status")
        .then(setStatus)
        .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Unable to load mailbox status."));
      if (status?.connected) void loadMessages();
    };
    window.addEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(WORKSPACE_REFRESH_EVENT, refresh);
  }, [canRead, status?.connected]);

  async function openThread(threadId: string | null) {
    if (!threadId) return;
    setLoadingThread(true);
    setInboxError("");
    try {
      const result = await emailRequest<{ messages: MailboxThreadMessage[] }>(`/email/threads/${threadId}`);
      setSelectedThread(result.messages);
    } catch (loadError) {
      setInboxError(loadError instanceof Error ? loadError.message : "Unable to open the message thread.");
    } finally {
      setLoadingThread(false);
    }
  }

  async function connectMailbox() {
    setConnecting(true);
    setError("");
    try {
      const response = await emailRequest<{ authorization_url: string }>("/email/oauth/start");
      window.location.assign(response.authorization_url);
    } catch (connectError) {
      setConnecting(false);
      setError(connectError instanceof Error ? connectError.message : "Unable to start Gmail connection.");
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError("");
    setSendResult("");
    try {
      const result = await emailRequest<{ message_id: string }>("/email/messages/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: recipient, subject, body }),
      });
      setSendResult(`Message sent successfully (ID: ${result.message_id}).`);
      setRecipient("");
      await loadMessages();
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Unable to send the message.");
    } finally {
      setSending(false);
    }
  }

  function searchMessages(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = searchInput.trim();
    setActiveQuery(nextQuery);
    void loadMessages(nextQuery);
  }

  if (!canRead) return null;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <CardTitle>Shared GOAG mailbox</CardTitle>
            <CardDescription>Only the Managing Director and Store Manager can access this mailbox.</CardDescription>
          </div>
          <Badge variant={status?.connected ? "default" : "secondary"}>
            {status?.connected ? "Connected" : status ? "Not connected" : "Loading"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {error ? <p className="text-destructive">{error}</p> : null}
        {status?.mailbox_email ? <p className="font-medium">{status.mailbox_email}</p> : null}
        <p className="text-muted-foreground">{status?.message ?? "Checking the shared Google Gmail connection."}</p>
        {status?.connected ? (
          <div className="space-y-5">
            <section className="space-y-3 rounded-md border p-4">
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <h3 className="font-medium">Inbox</h3>
                  <p className="text-muted-foreground">Search the shared mailbox with Gmail filters such as `from:` or `is:unread`.</p>
                </div>
                <Button type="button" variant="outline" disabled={loadingMessages} onClick={() => void loadMessages()}>
                  {loadingMessages ? "Refreshing…" : "Refresh"}
                </Button>
              </div>
              <form className="flex flex-col gap-2 sm:flex-row" onSubmit={searchMessages}>
                <Input
                  aria-label="Search mailbox"
                  placeholder="Search messages, e.g. from:supplier@example.com"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                />
                <Button type="submit" variant="secondary" disabled={loadingMessages}>Search</Button>
              </form>
              {inboxError ? <p className="text-destructive">{inboxError}</p> : null}
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>From</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead className="hidden md:table-cell">Preview</TableHead>
                      <TableHead className="text-right">Received</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {messages.map((message) => (
                      <TableRow key={message.id} data-state={message.unread ? "unread" : undefined}>
                        <TableCell className={message.unread ? "font-semibold" : ""}>{message.sender}</TableCell>
                        <TableCell>
                          <Button
                            type="button"
                            variant="link"
                            className="h-auto max-w-64 justify-start px-0 text-left"
                            disabled={loadingThread}
                            onClick={() => void openThread(message.thread_id)}
                          >
                            {message.subject}
                          </Button>
                        </TableCell>
                        <TableCell className="hidden max-w-80 truncate text-muted-foreground md:table-cell">{message.snippet}</TableCell>
                        <TableCell className="text-right text-muted-foreground">{formatDate(message.received_at)}</TableCell>
                      </TableRow>
                    ))}
                    {!loadingMessages && messages.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">No messages found.</TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              </div>
            </section>

            {selectedThread.length > 0 ? (
              <section className="space-y-3 rounded-md border p-4">
                <div>
                  <h3 className="font-medium">Message thread</h3>
                  <p className="text-muted-foreground">Opened from the shared GOAG mailbox.</p>
                </div>
                {selectedThread.map((message) => (
                  <article key={message.id} className="space-y-2 rounded-md bg-muted/40 p-4">
                    <div className="flex flex-col justify-between gap-1 sm:flex-row">
                      <p className="font-medium">{message.subject}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(message.sent_at)}</p>
                    </div>
                    <p className="text-xs text-muted-foreground">From {message.sender} · To {message.recipients || "—"}</p>
                    <p className="whitespace-pre-wrap">{message.body}</p>
                  </article>
                ))}
              </section>
            ) : null}

            {canSend ? (
              <form className="space-y-3 rounded-md border p-4" onSubmit={(event) => void sendMessage(event)}>
                <div>
                  <h3 className="font-medium">Send a message</h3>
                  <p className="text-muted-foreground">Messages are sent from the connected GOAG mailbox.</p>
                </div>
                <Input type="email" required placeholder="Recipient email" value={recipient} onChange={(event) => setRecipient(event.target.value)} />
                <Input required placeholder="Subject" value={subject} onChange={(event) => setSubject(event.target.value)} />
                <textarea
                  className="min-h-28 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  required
                  placeholder="Message"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                />
                {sendResult ? <p className="text-emerald-700">{sendResult}</p> : null}
                <Button type="submit" disabled={sending}>{sending ? "Sending…" : "Send message"}</Button>
              </form>
            ) : null}
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" disabled={!canManage || !status?.configured || connecting} onClick={() => void connectMailbox()}>
              {connecting ? "Opening Google…" : "Connect shared Gmail mailbox"}
            </Button>
            {!status?.configured ? <span className="text-xs text-muted-foreground">OAuth credentials are required first.</span> : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
