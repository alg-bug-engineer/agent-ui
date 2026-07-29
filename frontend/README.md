# 城市信控智能体前端

本前端实现 Act 1（全域感知）、Act 2（问题诊断）和 Act 6（复盘进化）。

## 目录

```text
act1/                  Act 1 业务组件
act2/                  Act 2 业务组件
act6/                  Act 6 业务组件
src/                   通用壳层、地图内核、状态和数据访问
public/data/           JSON/GeoJSON 演示数据
tests/                 数据契约测试
```

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173/`

## 环境变量配置

复制环境变量模板：

```bash
cp .env.example .env.local
```

填写：

```dotenv
VITE_APP_TITLE=济南城市信控智能体
VITE_DATA_BASE_URL=/data
VITE_AMAP_KEY=
VITE_AMAP_SECURITY_CODE=
VITE_AMAP_VIEW_MODE=2D
VITE_MAP_CENTER_LNG=117.1098
VITE_MAP_CENTER_LAT=36.6632
VITE_TARGET_LNG=117.111368
VITE_TARGET_LAT=36.663092
VITE_ACT1_DETECTION_SECONDS=10
VITE_ACT1_AUTO_PROCESS_SECONDS=10
```

`.env` 已被项目根目录的忽略规则排除，不应提交真实 Key 或安全密钥。

未配置高德 Key 或高德加载失败时，界面会明确显示配置错误，不再使用会导致业务图形与地图错位的伪底图。

本项目默认且建议保持 `VITE_AMAP_VIEW_MODE=2D`。所有监测点、图钉、设备、渠化与溯源图层均为高德地理覆盖物，拖拽和缩放后仍与道路坐标贴合。

所有环境变量均由 `src/config/runtime.ts` 统一读取和提供默认值，业务组件不直接访问 `import.meta.env`。

## 构建与测试

```bash
npm test
npm run build
```

## 数据替换

页面通过 `src/services/dataRepository.ts` 使用 HTTP 读取 `public/data/` 下的数据。

后端接入时，只需：

1. 保持现有 JSON 字段契约；
2. 将 `dataRepository` 中的静态 URL 替换为后端接口；
3. 无需修改各 Act 组件中的展示逻辑。
