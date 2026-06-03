import type { CSSProperties } from "react";

import type { CatalogProduct, ProductPhotos } from "../types";
import { CARD_FALLBACK_IMAGE, setFallbackImage } from "../lib/catalog-core";
import { getPrimaryProductImage } from "../lib/catalog-products";
import { ThumbStrip } from "./Thumb";

interface ProductCardProps {
  item: CatalogProduct;
  photos?: ProductPhotos | null;
  index: number;
  onOpen: () => void;
  showSalesHighlight?: boolean;
  salesRank?: number;
}

function formatMonthlySales(value: number): string {
  const maximumFractionDigits = Number.isInteger(value) ? 0 : 1;
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits }).format(value);
}

export default function ProductCard({
  item,
  photos,
  index,
  onOpen,
  showSalesHighlight = false,
  salesRank,
}: ProductCardProps): JSX.Element {
  const previewImage = getPrimaryProductImage(photos, item.cover) || CARD_FALLBACK_IMAGE;
  const shouldShowSales = showSalesHighlight && item.monthlySales > 0;

  return (
    <article className="product-card" style={{ "--stagger": `${Math.min(index * 70, 700)}ms` } as CSSProperties}>
      <button
        type="button"
        className="card-hitbox"
        onClick={onOpen}
        aria-label={`Abrir detalhes de ${item.name || "produto"}`}
      >
        <div className="media">
          <img
            src={previewImage}
            alt={item.name || "Produto"}
            loading="lazy"
            decoding="async"
            width="900"
            height="700"
            onError={(event) => setFallbackImage(event, CARD_FALLBACK_IMAGE)}
          />
          <div className="media-overlay"></div>
          <span className="chip chip-code">#{item.code}</span>
          <span className="chip chip-category">{item.category}</span>
        </div>

        <div className="card-body">
          {shouldShowSales && (
            <div className="card-sales-row">
              {salesRank ? <span className="card-sales-rank">Top {salesRank}</span> : null}
              <span className="card-sales-copy">{formatMonthlySales(item.monthlySales)} vendas no mês</span>
            </div>
          )}
          <h3>{item.name || "Produto"}</h3>
          <p className="description">{item.description || "Descrição indisponível para este produto."}</p>
          <span className="expand-label">Abrir galeria completa</span>
        </div>
      </button>

      <ThumbStrip photos={photos} />
    </article>
  );
}
