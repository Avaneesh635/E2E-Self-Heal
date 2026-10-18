import { useState } from "react";

export function CatalogRowDetail() {
  const [open, setOpen] = useState(false);

  return (
    <section aria-labelledby="catalog-detail-heading">
      <h2 id="catalog-detail-heading">Product detail</h2>
      <button type="button" className="catalog-detail" onClick={() => setOpen(true)}>
        Details
      </button>
      {open && <p id="catalog-detail">Desk Lamp: in stock</p>}
    </section>
  );
}
