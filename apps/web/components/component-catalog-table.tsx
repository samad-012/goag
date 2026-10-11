"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type CatalogComponent = {
  id: string;
  code: string;
  name: string;
  category: string;
  remarks: string;
};

type InventoryUnit = {
  component_id: string;
  status: string;
};

export function ComponentCatalogTable({ components, units }: { components: CatalogComponent[]; units: InventoryUnit[] }) {
  const [search, setSearch] = useState("");
  const stockByComponent = useMemo(() => {
    const counts = new Map<string, number>();
    for (const unit of units) {
      if (unit.status === "in_stock") counts.set(unit.component_id, (counts.get(unit.component_id) ?? 0) + 1);
    }
    return counts;
  }, [units]);
  const filteredComponents = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return components;
    return components.filter((component) => `${component.code} ${component.name} ${component.category}`.toLowerCase().includes(query));
  }, [components, search]);

  return (
    <Card>
      <CardHeader className="gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>Component catalog</CardTitle>
            <CardDescription>Search the GOAG catalog and check serialized stock before issuing components.</CardDescription>
          </div>
          <Badge variant="outline" className="w-fit">{components.length} components</Badge>
        </div>
        <div className="max-w-md">
          <Input aria-label="Search component catalog" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search code, name, or category" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-hidden rounded-lg border">
          <Table>
            <TableCaption className="sr-only">Available GOAG components and current serialized stock.</TableCaption>
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="w-36">Code</TableHead>
                <TableHead>Component</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">Quantity</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredComponents.map((component) => {
                const quantity = stockByComponent.get(component.id) ?? 0;
                return (
                  <TableRow key={component.id}>
                    <TableCell className="font-mono text-xs font-medium">{component.code}</TableCell>
                    <TableCell>
                      <div className="font-medium">{component.name}</div>
                      {component.remarks && <div className="max-w-xs truncate text-xs text-muted-foreground" title={component.remarks}>{component.remarks}</div>}
                    </TableCell>
                    <TableCell><Badge variant="outline">{component.category}</Badge></TableCell>
                    <TableCell className="text-right"><Badge variant="outline">{quantity}</Badge></TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        {!filteredComponents.length && <p className="py-6 text-center text-sm text-muted-foreground">No components match your search.</p>}
        <p className="mt-3 text-xs text-muted-foreground">Quantity counts inventory units currently marked in stock. Serial numbers are recorded when units are received or issued.</p>
      </CardContent>
    </Card>
  );
}
