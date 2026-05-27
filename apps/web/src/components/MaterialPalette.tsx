"use client";

export const materials = [
  { id: "air", label: "ՕԴ", color: "#cfe8ff", flukaName: "AIR", density: 0.00120479 },
  { id: "lead", label: "ԿԱՊԱՐ", color: "#4b5563", flukaName: "LEAD", density: 11.35 },
  { id: "water", label: "ՋՈՒՐ", color: "#38bdf8", flukaName: "WATER", density: 1.0 },
  { id: "concrete", label: "ԲԵՏՈՆ", color: "#9ca3af", flukaName: "CONCRETE", density: 2.3 },
  { id: "silicon", label: "ՍԻԼԻՑԻՈՒՄ", color: "#f59e0b", flukaName: "SILICON", density: 2.329 },
  { id: "wood", label: "ՓԱՅՏ", color: "#8b5a2b", flukaName: "WOOD", density: 0.7 },
  { id: "glass", label: "ԱՊԱԿԻ", color: "#9be7ff", flukaName: "GLASS", density: 2.5 },
  { id: "tissue", label: "ՀՅՈՒՍՎԱԾՔ", color: "#f2a7a0", flukaName: "TISSUE", density: 1.0 },
  { id: "steel", label: "ՊՈՂՊԱՏ", color: "#7c8794", flukaName: "STEEL", density: 7.85 },
  { id: "rubber", label: "ՌԵՏԻՆ", color: "#101820", flukaName: "RUBBER", density: 1.1 },
  { id: "plastic", label: "ՊԼԱՍՏԻԿ", color: "#facc15", flukaName: "PLASTIC", density: 0.95 },
] as const;

type MaterialPaletteProps = {
  selectedId?: string;
  onSelect?: (materialId: string) => void;
};

export function MaterialPalette({ selectedId, onSelect }: MaterialPaletteProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <strong>Նյութեր</strong>
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
