# Chart_Engine Migration Guide

## Overview

The `Chart_Engine/` directory (a vendored copy of TradingView's Lightweight Charts) has been removed from the repository. The project now uses the official `lightweight-charts` npm package via the `ui/` frontend.

## What Changed

| Before | After |
|--------|-------|
| `Chart_Engine/` (vendored copy, ~50MB) | `lightweight-charts@^5.2.0` npm package |
| Manual updates to track upstream | Automatic via `npm update` |
| Custom TypeScript declarations | Official type definitions included |
| No version lock | Pinned in `ui/package.json` |

## Migration Steps for Users

1. **Update imports** — Change from local paths to npm package:
   ```typescript
   // Before (local vendored copy)
   import { createChart } from '../../Chart_Engine/dist/lightweight-charts.standalone.production';
   
   // After (npm package)
   import { createChart } from 'lightweight-charts';
   ```

2. **Install dependencies** — The `lightweight-charts` package is already in `ui/package.json`:
   ```bash
   cd ui && npm install
   ```

3. **Verify API compatibility** — The npm package exposes the exact same API:
   - `createChart()`, `createChartEx()`, `createYieldCurveChart()`, `createOptionsChart()`
   - All series types: `LineSeries`, `CandlestickSeries`, `BarSeries`, `HistogramSeries`, `AreaSeries`, `BaselineSeries`
   - All plugins: text watermark, image watermark, series markers, etc.

4. **Remove old references** — Delete any remaining imports pointing to `Chart_Engine/`:
   ```bash
   grep -r "Chart_Engine" ui/ --include="*.ts" --include="*.tsx" --include="*.js"
   ```

## Why This Change

- **Reduced repository size**: Removed ~50MB of vendored code
- **Automatic updates**: npm package receives upstream fixes automatically
- **Smaller Docker images**: No need to build Chart_Engine in Docker
- **Standard tooling**: npm/yarn/pnpm handle versioning and integrity checks

## If You Experience Issues

1. Check that `lightweight-charts@^5.2.0` is installed: `npm ls lightweight-charts` in `ui/`
2. Verify your imports use the package name, not a relative path
3. The `createChart` and `createChartEx` functions have identical signatures

For API documentation, see: https://tradingview.github.io/lightweight-charts/
