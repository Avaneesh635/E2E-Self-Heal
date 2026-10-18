import { useState, type ChangeEvent } from "react";

const PRODUCTS = ["Desk Lamp", "Wall Clock", "Office Chair"];

export function CatalogSearch() {
  const [query, setQuery] = useState("");

  const results = PRODUCTS.filter((product) =>
    product.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <section aria-labelledby="catalog-search-heading">
      <h2 id="catalog-search-heading">Find a product</h2>
      <label htmlFor="catalog-search">Search</label>
      <input
        id="catalog-search"
        type="search"
        placeholder="Search products"
        defaultValue=""
        onChange={(event: ChangeEvent<HTMLInputElement>) => setQuery(event.target.value)}
      />
      <ul id="catalog-results">
        {results.map((product) => (
          <li key={product}>{product}</li>
        ))}
      </ul>
    </section>
  );
}
