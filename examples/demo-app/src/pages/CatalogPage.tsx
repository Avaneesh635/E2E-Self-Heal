import { CatalogPager } from "../components/catalog/CatalogPager";
import { CatalogRowDetail } from "../components/catalog/CatalogRowDetail";
import { CatalogSearch } from "../components/catalog/CatalogSearch";
import { CatalogSort } from "../components/catalog/CatalogSort";

export function CatalogPage() {
  return (
    <section aria-labelledby="catalog-heading">
      <h1 id="catalog-heading">Catalog</h1>
      <CatalogSearch />
      <CatalogSort />
      <CatalogPager />
      <CatalogRowDetail />
    </section>
  );
}
