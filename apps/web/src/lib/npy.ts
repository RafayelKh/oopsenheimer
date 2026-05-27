export function parseNpyFloat32(buffer: ArrayBuffer): { shape: number[]; values: Float32Array } {
  const bytes = new Uint8Array(buffer);
  const magic = String.fromCharCode(...bytes.slice(0, 6));
  if (magic !== "\x93NUMPY") {
    throw new Error("Դոզայի արտեֆակտը NumPy .npy ֆայլ չէ։");
  }

  const major = bytes[6];
  const view = new DataView(buffer);
  const headerLength = major === 1 ? view.getUint16(8, true) : view.getUint32(8, true);
  const headerOffset = major === 1 ? 10 : 12;
  const dataOffset = headerOffset + headerLength;
  const header = new TextDecoder("latin1").decode(bytes.slice(headerOffset, dataOffset));

  if (!header.includes("'descr': '<f4'") && !header.includes('"descr": "<f4"')) {
    throw new Error("Աջակցվում են միայն little-endian float32 .npy դոզայի զանգվածները։");
  }
  if (header.includes("'fortran_order': True") || header.includes('"fortran_order": true')) {
    throw new Error("Ֆորտրան դասավորությամբ .npy դոզայի զանգվածները չեն աջակցվում։");
  }

  const shapeMatch = header.match(/['"]shape['"]:\s*\(([^)]*)\)/);
  if (!shapeMatch) {
    throw new Error("Չհաջողվեց կարդալ .npy զանգվածի չափերը։");
  }
  const shape = shapeMatch[1]
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map(Number);
  const valueCount = shape.reduce((product, value) => product * value, 1);
  return { shape, values: new Float32Array(buffer, dataOffset, valueCount) };
}

export function formatDose(value: number): string {
  if (value === 0) {
    return "0";
  }
  const absolute = Math.abs(value);
  if (absolute < 0.001 || absolute >= 1000) {
    return value.toExponential(3);
  }
  return value.toFixed(4);
}

export function doseUnit(quantity?: string, explicitUnit?: string): string {
  if (explicitUnit) {
    return explicitUnit;
  }
  const normalized = quantity?.toUpperCase() ?? "DOSE";
  if (normalized === "DOSE-H2O") {
    return "Gy";
  }
  if (normalized.startsWith("DOSE")) {
    return "GeV/g";
  }
  return "կամայական միավոր";
}

export function formatDoseWithUnit(value: number, unit: string): string {
  return `${formatDose(value)} ${unit}`;
}

export function normalizedDose(value: number, min: number, max: number): number {
  const span = max - min;
  return span > 0 ? Math.max(0, Math.min(1, (value - min) / span)) : 0;
}

export function doseColor(value: number, min: number, max: number): string {
  const clamped = normalizedDose(value, min, max);
  const hue = 74 - clamped * 64;
  const lightness = 22 + clamped * 48;
  return `hsl(${hue} 95% ${lightness}%)`;
}
