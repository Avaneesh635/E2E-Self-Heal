import { useState } from "react";

type Row = {
  name: string;
  price: number;
};

const ROWS: Row[] = [
  { name: "Office Chair", price: 120 },
  { name: "Desk Lamp", price: 20 },
  { name: "Wall Clock", price: 35 },
];

export function CatalogSort() {
  const [rows, setRows] = useState(ROWS);

  const byPrice = [...rows].sort((left, right) => left.price - right.price);

  return (
    <section aria-labelledby="catalog-sort-heading">
      <h2 id="catalog-sort-heading">Sort the catalog</h2>
      <button type="button" className="catalog-sort" onClick={() => setRows(byPrice)}>
        Sort by price
      </button>
      <ul id="catalog-rows">
        {rows.map((row: Row) => (
          <li key={row.name}>
            <span>{row.name}</span> <span>${row.price}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
