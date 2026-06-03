import type { ProductPhotos } from "../types";
import { THUMB_FALLBACK_IMAGE, setFallbackImage } from "../lib/catalog-core";

interface ThumbProps {
  image?: string | null;
  label: string;
}

export function Thumb({ image, label }: ThumbProps): JSX.Element {
  return (
    <figure className="thumb">
      <img
        src={image || THUMB_FALLBACK_IMAGE}
        alt={label}
        loading="lazy"
        decoding="async"
        width="240"
        height="240"
        onError={(event) => setFallbackImage(event, THUMB_FALLBACK_IMAGE)}
      />
      <figcaption>{label}</figcaption>
    </figure>
  );
}

interface ThumbStripProps {
  photos?: ProductPhotos | null;
}

export function ThumbStrip({ photos }: ThumbStripProps): JSX.Element {
  return (
    <div className="thumb-strip" aria-label="Fotos do produto">
      <Thumb image={photos?.ambient} label="Ambientada" />
      <Thumb image={photos?.white_background} label="Fundo branco" />
      <Thumb image={photos?.measures} label="Medidas" />
    </div>
  );
}
