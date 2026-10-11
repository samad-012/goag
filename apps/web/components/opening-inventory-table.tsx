"use client";

import { useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Component = {
  id: string;
  code: string;
  name: string;
  category: string;
};

type OpeningRow = {
  id?: string;
  component_id: string;
  serial_number: string;
  condition: string;
  location: string;
  saveState: "draft" | "saving" | "saved" | "error";
  error?: string;
};

const fieldClassName =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring";

async function saveInventoryUnit(payload: { component_id: string; serial_number: string; condition: string; location: string }) {
  const response = await fetch("/api/backend/inventory/units", {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Unable to save inventory unit (${response.status})`);
  }
  return (await response.json()) as { id: string };
}

function emptyRow(): OpeningRow {
  return { component_id: "", serial_number: "", condition: "good", location: "store", saveState: "draft" };
}

export function OpeningInventoryTable({ components, onSaved }: { components: Component[]; onSaved: () => void }) {
  const [rows, setRows] = useState<OpeningRow[]>([emptyRow()]);
  const [search, setSearch] = useState("");
  const savingRows = useRef(new Set<number>());
  const filteredComponents = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return components;
    return components.filter((component) => `${component.code} ${component.name} ${component.category}`.toLowerCase().includes(query));
  }, [components, search]);

  const updateRow = (index: number, patch: Partial<OpeningRow>) => {
    setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch, saveState: row.id ? row.saveState : "draft", error: undefined } : row));
  };

  const saveRow = async (index: number) => {
    const row = rows[index];
    if (!row || row.id || !row.component_id || !row.serial_number.trim() || savingRows.current.has(index)) return;
    savingRows.current.add(index);
    setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, saveState: "saving", error: undefined } : item));
    try {
      const saved = await saveInventoryUnit({
        component_id: row.component_id,
        serial_number: row.serial_number.trim(),
        condition: row.condition,
        location: row.location.trim() || "store",
      });
      setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, id: saved.id, saveState: "saved" } : item));
      onSaved();
    } catch (error) {
      setRows((current) => current.map((item, rowIndex) => rowIndex === index ? { ...item, saveState: "error", error: error instanceof Error ? error.message : "Unable to save row" } : item));
    } finally {
      savingRows.current.delete(index);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>Opening inventory</CardTitle>
            <CardDescription>Enter the components from the paper book. Each completed row is saved automatically as serialized stock.</CardDescription>
          </div>
          <Button type="button" variant="outline" onClick={() => setRows((current) => [...current, emptyRow()])}>Add row</Button>
        </div>
        <div className="max-w-md pt-2"><Label htmlFor="opening-inventory-search">Search components</Label><Input id="opening-inventory-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by code, name, or category" /></div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader><TableRow><TableHead className="min-w-56">Component</TableHead><TableHead className="min-w-44">Serial number</TableHead><TableHead className="min-w-32">Condition</TableHead><TableHead className="min-w-36">Location</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
            <TableBody>
              {rows.map((row, index) => (
                <TableRow key={row.id ?? `draft-${index}`}>
                  <TableCell><select aria-label={`Component row ${index + 1}`} className={fieldClassName} disabled={Boolean(row.id)} value={row.component_id} onChange={(event) => updateRow(index, { component_id: event.target.value })} onBlur={() => void saveRow(index)}><option value="">Select component</option>{filteredComponents.map((component) => <option key={component.id} value={component.id}>{component.code} · {component.name}</option>)}</select></TableCell>
                  <TableCell><Input aria-label={`Serial number row ${index + 1}`} disabled={Boolean(row.id)} value={row.serial_number} onChange={(event) => updateRow(index, { serial_number: event.target.value })} onBlur={() => void saveRow(index)} placeholder="Serial number" /></TableCell>
                  <TableCell><select aria-label={`Condition row ${index + 1}`} className={fieldClassName} disabled={Boolean(row.id)} value={row.condition} onChange={(event) => updateRow(index, { condition: event.target.value })} onBlur={() => void saveRow(index)}><option value="good">Good</option><option value="new">New</option><option value="used">Used</option><option value="damaged">Damaged</option></select></TableCell>
                  <TableCell><Input aria-label={`Location row ${index + 1}`} disabled={Boolean(row.id)} value={row.location} onChange={(event) => updateRow(index, { location: event.target.value })} onBlur={() => void saveRow(index)} /></TableCell>
                  <TableCell>{row.saveState === "saved" && <Badge>Saved</Badge>}{row.saveState === "saving" && <Badge variant="secondary">Saving…</Badge>}{row.saveState === "draft" && <Badge variant="outline">Draft</Badge>}{row.saveState === "error" && <div className="space-y-1"><Badge variant="destructive">Error</Badge><p className="max-w-48 text-xs text-destructive">{row.error}</p></div>}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Rows are not saved until a component and serial number are present. Saved rows become read-only to protect inventory history.</p>
      </CardContent>
    </Card>
  );
}
