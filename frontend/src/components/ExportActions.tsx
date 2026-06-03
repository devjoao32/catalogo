import type { CatalogExportFormat } from "../types";

interface ExportActionsProps {
  title: string;
  note?: string;
  onExport: (format: CatalogExportFormat) => void;
  disabled?: boolean;
  compact?: boolean;
  includeTechnicalSheet?: boolean;
}

const EXPORT_BUTTONS: Array<{ format: CatalogExportFormat; label: string }> = [
  { format: "csv", label: "CSV" },
  { format: "xlsx", label: "Excel" },
  { format: "pdf", label: "PDF" },
  { format: "zip", label: "ZIP" },
  { format: "json", label: "JSON" },
];

export default function ExportActions({
  title,
  note,
  onExport,
  disabled = false,
  compact = false,
  includeTechnicalSheet = false,
}: ExportActionsProps): JSX.Element {
  const buttons = includeTechnicalSheet
    ? [
        { format: "ficha" as CatalogExportFormat, label: "Ficha técnica" },
        ...EXPORT_BUTTONS,
      ]
    : EXPORT_BUTTONS;

  return (
    <section className={`export-panel ${compact ? "is-compact" : ""}`} aria-label={title}>
      <div className="export-copy">
        <strong>{title}</strong>
        {note ? <span>{note}</span> : null}
      </div>

      <div className="export-actions">
        {buttons.map((item) => (
          <button
            key={item.format}
            type="button"
            className="export-button"
            onClick={() => onExport(item.format)}
            disabled={disabled}
          >
            {item.label}
          </button>
        ))}
      </div>
    </section>
  );
}
