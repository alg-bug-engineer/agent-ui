/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE?: string
  readonly VITE_APP_CITY?: string
  readonly VITE_DATA_MODE?: string
  readonly VITE_DATA_BASE_URL?: string
  readonly VITE_AMAP_KEY?: string
  readonly VITE_AMAP_SECURITY_CODE?: string
  readonly VITE_AMAP_VERSION?: string
  readonly VITE_LOCA_VERSION?: string
  readonly VITE_AMAP_STYLE?: string
  readonly VITE_AMAP_VIEW_MODE?: string
  readonly VITE_MAP_FALLBACK_ENABLED?: string
  readonly VITE_MAP_CENTER_LNG?: string
  readonly VITE_MAP_CENTER_LAT?: string
  readonly VITE_TARGET_LNG?: string
  readonly VITE_TARGET_LAT?: string
  readonly VITE_MAP_OVERVIEW_ZOOM?: string
  readonly VITE_ACT1_DETECTION_SECONDS?: string
  readonly VITE_ACT1_AUTO_PROCESS_SECONDS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
