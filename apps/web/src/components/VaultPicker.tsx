"use client";

import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { api } from "@/lib/api";
import type { Vault } from "@/types";

const VAULT_KEY = "pkb.selected-vault";

export function selectedVault(): string {
  if (typeof window === "undefined") return "default";
  return window.localStorage.getItem(VAULT_KEY) || "default";
}

export function setSelectedVault(vaultId: string) {
  window.localStorage.setItem(VAULT_KEY, vaultId);
  window.dispatchEvent(new CustomEvent("pkb:vault-changed", { detail: vaultId }));
}

export default function VaultPicker() {
  const [vaults, setVaults] = useState<Vault[]>([]);
  const [value, setValue] = useState("default");

  useEffect(() => {
    setValue(selectedVault());
    api.getVaults().then(({ data }) => setVaults(data.vaults)).catch(() => undefined);
  }, []);

  const options = vaults.length ? vaults : [{ id: "default", name: "Default vault" }];
  return (
    <label className="flex items-center gap-1.5 text-xs font-medium text-ink-500">
      <Database className="h-3.5 w-3.5" />
      <span className="sr-only">Active vault</span>
      <select
        aria-label="Active vault"
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          setSelectedVault(event.target.value);
        }}
        className="max-w-36 rounded-md border border-ink-200 bg-white px-2 py-1 text-xs text-ink-700"
      >
        {options.map((vault) => <option key={vault.id} value={vault.id}>{vault.name}</option>)}
      </select>
    </label>
  );
}
