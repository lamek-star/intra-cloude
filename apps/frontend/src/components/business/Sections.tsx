"use client";

import { editionOf } from "@/lib/business";
import { useBusiness } from "./BusinessApp";
import { MedicineImportButton } from "./MedicineImport";
import RecordSection from "./RecordSection";

// Simple list-and-add screens. Which fields exist is the App Platform template's business; the
// labels and grouping here follow the reference spare-parts application's terminology.

export function ProductsSection() {
  const { instance, schema } = useBusiness();
  if (editionOf(schema) === "pharmacy") {
    return (
      <RecordSection
        modelKey="part"
        title="Medicines"
        description="The medicines you stock and sell. Open one to see its item numbers, stock, pictures and label."
        noun="Medicine"
        searchPlaceholder="Search medicines by name"
        emptyHint="Add your first medicine, or import a medicines catalogue, then receive some stock."
        columns={[
          { key: "name", label: "Name" },
          { key: "generic_name", label: "Generic name" },
          { key: "pack", label: "Pack" },
          { key: "storage_location", label: "Shelf" },
          { key: "list_price", label: "Price" },
        ]}
        fields={[
          { key: "name", label: "Name", required: true },
          { key: "generic_name", label: "Generic name", placeholder: "e.g. Paracetamol 500 mg" },
          { key: "pack", label: "Pack", placeholder: "e.g. 10 tablets in a strip" },
          { key: "manufacturer", label: "Manufacturer" },
          { key: "storage_location", label: "Shelf location", placeholder: "e.g. Shelf B3" },
          { key: "list_price", label: "Your price", kind: "money" },
          { key: "standard_cost", label: "Cost", kind: "money" },
        ]}
        linkKey="name"
        rowHref={(row) => `/apps/${instance.id}/products/${row.id}`}
        actions={(reload) => <MedicineImportButton onImported={reload} />}
      />
    );
  }
  return (
    <RecordSection
      modelKey="part"
      title="Products"
      description="The parts you buy and sell. Open one to see its part numbers, stock, movements and files."
      noun="Product"
      searchPlaceholder="Search products by name"
      emptyHint="Add your first product, then give it part numbers and receive some stock."
      columns={[
        { key: "name", label: "Name" },
        { key: "unit_of_measure", label: "Unit" },
        { key: "list_price", label: "List price" },
      ]}
      fields={[
        { key: "name", label: "Name", required: true },
        { key: "description", label: "Description" },
        { key: "unit_of_measure", label: "Unit of measure", placeholder: "each, set, litre…" },
        { key: "list_price", label: "List price", kind: "money" },
        { key: "standard_cost", label: "Standard cost", kind: "money" },
      ]}
      linkKey="name"
      rowHref={(row) => `/apps/${instance.id}/products/${row.id}`}
    />
  );
}

export function SuppliersSection() {
  return (
    <RecordSection
      modelKey="supplier"
      title="Suppliers"
      description="Who you buy from."
      noun="Supplier"
      searchPlaceholder="Search suppliers by name"
      emptyHint="Add the suppliers you buy stock from."
      columns={[
        { key: "name", label: "Name" },
        { key: "contact_email", label: "Email" },
        { key: "contact_phone", label: "Phone" },
      ]}
      fields={[
        { key: "name", label: "Name", required: true },
        { key: "contact_email", label: "Email" },
        { key: "contact_phone", label: "Phone" },
      ]}
    />
  );
}

export function CustomersSection() {
  return (
    <RecordSection
      modelKey="customer"
      title="Customers"
      description="Who you sell to."
      noun="Customer"
      searchPlaceholder="Search customers by name"
      emptyHint="Add a customer so you can record a sale."
      columns={[
        { key: "name", label: "Name" },
        { key: "contact_email", label: "Email" },
        { key: "contact_phone", label: "Phone" },
      ]}
      fields={[
        { key: "name", label: "Name", required: true },
        { key: "contact_email", label: "Email" },
        { key: "contact_phone", label: "Phone" },
      ]}
    />
  );
}

export function WarehousesSection() {
  return (
    <RecordSection
      modelKey="warehouse"
      title="Warehouses"
      description="Where stock is kept. Every quantity belongs to a warehouse."
      noun="Warehouse"
      searchPlaceholder="Search warehouses"
      emptyHint="Add at least one warehouse before receiving stock."
      columns={[
        { key: "name", label: "Name" },
        { key: "code", label: "Code" },
      ]}
      fields={[
        { key: "name", label: "Name", required: true },
        { key: "code", label: "Code", required: true, placeholder: "e.g. MAIN" },
      ]}
    />
  );
}
