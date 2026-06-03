import { UI_STATE_STORAGE_KEY } from "./catalog-core";

export interface PersistedUiState {
  query: string;
  category: string;
  brand: "nitrolux" | "pienza";
}

const FALLBACK_STATE: PersistedUiState = {
  query: "",
  category: "Todas",
  brand: "nitrolux",
};

export function readPersistedUiState(): PersistedUiState {
  if (typeof window === "undefined" || !window.localStorage) {
    return FALLBACK_STATE;
  }

  try {
    const rawValue = window.localStorage.getItem(UI_STATE_STORAGE_KEY);
    if (!rawValue) return FALLBACK_STATE;

    const parsed = JSON.parse(rawValue) as Partial<PersistedUiState>;
    return {
      query: typeof parsed.query === "string" ? parsed.query : FALLBACK_STATE.query,
      category:
        typeof parsed.category === "string" && parsed.category
          ? parsed.category
          : FALLBACK_STATE.category,
      brand: parsed.brand === "pienza" ? "pienza" : FALLBACK_STATE.brand,
    };
  } catch (error) {
    console.warn("Não foi possível ler estado de UI persistido.", error);
    return FALLBACK_STATE;
  }
}

export function persistUiState(state: PersistedUiState): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }

  try {
    window.localStorage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.warn("Não foi possível persistir estado de UI.", error);
  }
}
