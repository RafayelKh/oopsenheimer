"use client";

export const materials = [
  { id: "air", label: "AIR", color: "#cfe8ff", flukaName: "AIR", density: 0.00120479 },
  { id: "lead", label: "LEAD", color: "#4b5563", flukaName: "LEAD", density: 11.35 },
  { id: "water", label: "WATER", color: "#38bdf8", flukaName: "WATER", density: 1.0 },
  { id: "concrete", label: "CONCRETE", color: "#9ca3af", flukaName: "CONCRETE", density: 2.3 },
  { id: "silicon", label: "SILICON", color: "#f59e0b", flukaName: "SILICON", density: 2.329 },
  { id: "wood", label: "WOOD", color: "#8b5a2b", flukaName: "WOOD", density: 0.7 },
  { id: "glass", label: "GLASS", color: "#9be7ff", flukaName: "GLASS", density: 2.5 },
  { id: "tissue", label: "TISSUE", color: "#f2a7a0", flukaName: "TISSUE", density: 1.0 },
  { id: "steel", label: "STEEL", color: "#7c8794", flukaName: "STEEL", density: 7.85 },
  { id: "rubber", label: "RUBBER", color: "#101820", flukaName: "RUBBER", density: 1.1 },
  { id: "plastic", label: "PLASTIC", color: "#facc15", flukaName: "PLASTIC", density: 0.95 },
] as const;

type MaterialPaletteProps = {
  selectedId?: string;
  onSelect?: (materialId: string) => void;
};

export function MaterialPalette({ selectedId, onSelect }: MaterialPaletteProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Materials</strong>
      </div>
      <div className="panel-body material-list">
        {materials.map((material) => (
          <button
            className={`material-row ${selectedId === material.id ? "selected" : ""}`}
            disabled={!onSelect}
            key={material.id}
            onClick={() => onSelect?.(material.id)}
            type="button"
          >
            <span className="swatch" style={{ backgroundColor: material.color }} />
            <span>{material.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
