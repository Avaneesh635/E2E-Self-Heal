import { useState } from "react";

export function CatalogPager() {
  const [pageNumber, setPageNumber] = useState(1);

  return (
    <section aria-labelledby="catalog-pager-heading">
      <h2 id="catalog-pager-heading">Browse the catalog</h2>
      <button type="button" id="catalog-next" onClick={() => setPageNumber(2)}>
        Next page
      </button>
      <p id="catalog-page">Page {pageNumber} of 2</p>
    </section>
  );
}
