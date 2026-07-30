function envText(value: string | undefined, fallback: string): string {
  const normalized = value?.trim()
  return normalized || fallback
}

function envNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export const runtimeConfig = Object.freeze({
  app: {
    title: envText(import.meta.env.VITE_APP_TITLE, '济南交管支队信控智能体'),
    city: envText(import.meta.env.VITE_APP_CITY, '济南市'),
    dataMode: envText(import.meta.env.VITE_DATA_MODE, 'demo'),
  },
  data: {
    baseUrl: envText(import.meta.env.VITE_DATA_BASE_URL, '/data').replace(/\/+$/, ''),
  },
  amap: {
    key: envText(import.meta.env.VITE_AMAP_KEY, ''),
    securityCode: envText(import.meta.env.VITE_AMAP_SECURITY_CODE, ''),
    version: envText(import.meta.env.VITE_AMAP_VERSION, '2.0'),
    locaVersion: envText(import.meta.env.VITE_LOCA_VERSION, '2.0.0'),
    style: envText(import.meta.env.VITE_AMAP_STYLE, 'amap://styles/whitesmoke'),
    viewMode: envText(import.meta.env.VITE_AMAP_VIEW_MODE, '2D') === '3D' ? '3D' : '2D',
  },
  map: {
    center: [
      envNumber(import.meta.env.VITE_MAP_CENTER_LNG, 117.1098),
      envNumber(import.meta.env.VITE_MAP_CENTER_LAT, 36.6632),
    ] as [number, number],
    target: [
      envNumber(import.meta.env.VITE_TARGET_LNG, 117.111368),
      envNumber(import.meta.env.VITE_TARGET_LAT, 36.663092),
    ] as [number, number],
    overviewZoom: envNumber(import.meta.env.VITE_MAP_OVERVIEW_ZOOM, 15.4),
  },
  playback: {
    detectionSeconds: envNumber(import.meta.env.VITE_ACT1_DETECTION_SECONDS, 5),
    autoProcessSeconds: envNumber(import.meta.env.VITE_ACT1_AUTO_PROCESS_SECONDS, 10),
  },
})
