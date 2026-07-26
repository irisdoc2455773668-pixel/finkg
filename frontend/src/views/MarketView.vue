<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'
import { NCard, NGrid, NGi, NButton, NEmpty, NSpin } from 'naive-ui'

// ── State ──
const marketData = ref<any>(null)
const loading = ref(false)
const error = ref('')
const selectedCat = ref('全球股指')

const categoryKeys: Record<string, string> = {
  '全球股指': 'equity', '外汇市场': 'fx', '大宗商品': 'commodity',
  '数字货币': 'crypto', '国债利率': 'bond', '风险指标': 'risk',
}

// ── Chart interaction state ──
const chartContainer = ref<HTMLElement | null>(null)
const chartSvg = ref<SVGSVGElement | null>(null)
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const hoveredBar = ref<any>(null)
const mouseX = ref(0)
const mouseY = ref(0)

// Chart layout constants (SVG coordinate space)
const SVG_W = 900
const SVG_H = 350
const M = { top: 25, right: 30, bottom: 58, left: 68 }
const INNER_W = SVG_W - M.left - M.right
const INNER_H = SVG_H - M.top - M.bottom
const ZERO_Y = M.top + INNER_H / 2

// ── Data fetching ──
async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/market/indicators')
    marketData.value = data
  } catch (e: any) {
    console.error('Market data fetch error:', e)
    error.value = e?.response?.data?.detail || e?.message || 'Failed to load market data'
  } finally {
    loading.value = false
  }
}

onMounted(() => { fetchData() })

// ── Category helpers ──
function getCatItems(): any[] {
  if (!marketData.value?.categories) return []
  return marketData.value.categories[selectedCat.value] || []
}

function selectCat(cat: string) {
  selectedCat.value = cat
}

// ── Bar chart data ──
const barData = computed(() => {
  const items: any[] = []
  if (!marketData.value?.categories) return items
  for (const cat of Object.keys(categoryKeys)) {
    for (const item of marketData.value.categories[cat] || []) {
      items.push(item)
    }
  }
  return [...items]
    .sort((a, b) => Math.abs(b.changePct || 0) - Math.abs(a.changePct || 0))
    .slice(0, 15)
})

const maxAbsPct = computed(() => {
  const m = Math.max(...barData.value.map((i: any) => Math.abs(i.changePct || 0)), 0.01)
  return m * 1.15
})

// Y-axis grid lines
const yGridLines = computed(() => {
  const halfH = INNER_H / 2
  return [
    { y: M.top, label: `+${maxAbsPct.value.toFixed(2)}%` },
    { y: ZERO_Y - halfH * 0.5, label: `+${(maxAbsPct.value * 0.5).toFixed(2)}%` },
    { y: ZERO_Y, label: '0%', isZero: true },
    { y: ZERO_Y + halfH * 0.5, label: `-${(maxAbsPct.value * 0.5).toFixed(2)}%` },
    { y: M.top + INNER_H, label: `-${maxAbsPct.value.toFixed(2)}%` },
  ]
})

// ── Bar metrics ──
function barSlotX(i: number, total: number): number {
  const slotW = INNER_W / Math.max(total, 1)
  const bw = Math.min(slotW * 0.6, 36)
  return M.left + slotW * i + (slotW - bw) / 2
}
function barWidthVal(total: number): number {
  return Math.min(INNER_W / Math.max(total, 1) * 0.6, 36)
}
function barHeightVal(pct: number): number {
  return Math.abs(pct) / maxAbsPct.value * (INNER_H / 2)
}
function barYPos(pct: number): number {
  const h = barHeightVal(pct)
  return pct >= 0 ? ZERO_Y - h : ZERO_Y
}
function barFill(pct: number): string {
  return pct >= 0 ? '#dc2626' : '#059669'
}

// ── Tooltip ──
const tooltipStyle = computed(() => ({
  left: `${mouseX.value + 14}px`,
  top: `${mouseY.value - 12}px`,
}))

function onBarEnter(item: any) {
  if (!isDragging.value) hoveredBar.value = item
}
function onBarLeave() {
  hoveredBar.value = null
}

// ── Chart interactions ──
function onChartWheel(e: WheelEvent) {
  e.preventDefault()
  const rect = chartContainer.value?.getBoundingClientRect()
  if (!rect) return
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const factor = e.deltaY > 0 ? 0.92 : 1.08
  const newScale = Math.min(6, Math.max(0.25, scale.value * factor))
  panX.value = mx - (mx - panX.value) * (newScale / scale.value)
  panY.value = my - (my - panY.value) * (newScale / scale.value)
  scale.value = newScale
}

function onChartMouseDown(e: MouseEvent) {
  isDragging.value = true
  dragStartX.value = e.clientX - panX.value
  dragStartY.value = e.clientY - panY.value
}

function onChartMouseMove(e: MouseEvent) {
  if (isDragging.value) {
    panX.value = e.clientX - dragStartX.value
    panY.value = e.clientY - dragStartY.value
  }
  const rect = chartContainer.value?.getBoundingClientRect()
  if (rect) {
    mouseX.value = e.clientX - rect.left
    mouseY.value = e.clientY - rect.top
  }
}

function onChartMouseUp() {
  isDragging.value = false
}

function resetZoom() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
}

// ── Download chart as PNG ──
function downloadChart() {
  const svgEl = chartSvg.value
  if (!svgEl) return
  try {
    const clone = svgEl.cloneNode(true) as SVGSVGElement
    clone.setAttribute('width', String(SVG_W))
    clone.setAttribute('height', String(SVG_H))
    // Reset transform for full-chart export
    const innerG = clone.querySelector('g.chart-inner')
    if (innerG) innerG.setAttribute('transform', 'translate(0,0) scale(1)')
    const svgStr = new XMLSerializer().serializeToString(clone)
    const canvas = document.createElement('canvas')
    const dpr = 2
    canvas.width = SVG_W * dpr
    canvas.height = SVG_H * dpr
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    const img = new Image()
    const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    img.onload = () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      const a = document.createElement('a')
      a.download = `market-chart-${new Date().toISOString().slice(0, 10)}.png`
      a.href = canvas.toDataURL('image/png')
      a.click()
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      console.error('Failed to render SVG for download')
    }
    img.src = url
  } catch (e) {
    console.error('Download chart error:', e)
  }
}
</script>

<template>
  <div>
    <!-- Category pills -->
    <div class="cat-pills">
      <button
        v-for="cat in Object.keys(categoryKeys)"
        :key="cat"
        :class="['cat-pill', { active: selectedCat === cat }]"
        @click="selectCat(cat)"
      >{{ cat }}</button>
    </div>

    <!-- Error / Loading -->
    <div v-if="error" class="status-msg error">{{ error }}</div>
    <n-spin :show="loading" v-if="!marketData && loading" style="display:block;padding:40px;text-align:center" />

    <!-- Indicator cards -->
    <Transition name="grid-fade" mode="out-in">
      <n-grid
        v-if="getCatItems().length"
        :key="selectedCat"
        :cols="4"
        :x-gap="12"
        :y-gap="12"
        style="margin-bottom:24px"
      >
        <n-gi v-for="item in getCatItems()" :key="item.symbol">
          <n-card size="small" class="indicator-card">
            <div class="card-header">
              <span class="card-symbol">{{ item.symbol }}</span>
              <a
                v-if="item.sourceUrl && item.sourceUrl.length"
                :href="item.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="card-source-link"
                title="Open data source"
                @click.stop
              >&#8599;</a>
            </div>
            <div
              class="card-price"
              :style="{ color: (item.changePct ?? 0) >= 0 ? '#dc2626' : '#059669' }"
            >
              <a
                v-if="item.sourceUrl && item.sourceUrl.length"
                :href="item.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="card-price-link"
                :style="{ color: (item.changePct ?? 0) >= 0 ? '#dc2626' : '#059669' }"
                :title="'View ' + item.symbol + ' on source'"
                @click.stop
              >{{ item.price?.toLocaleString() }}</a>
              <span v-else>{{ item.price?.toLocaleString() }}</span>
              <span class="card-unit">{{ item.unit }}</span>
            </div>
            <div
              class="card-change"
              :style="{ color: (item.changePct ?? 0) >= 0 ? '#dc2626' : '#059669' }"
            >
              {{ (item.changePct ?? 0) >= 0 ? '+' : '' }}{{ item.changePct?.toFixed(2) }}%
            </div>
            <div class="card-meta">
              <span>{{ item.name }}</span>
              <span v-if="item.granularity" class="card-gran">{{ item.granularity }}</span>
            </div>
          </n-card>
        </n-gi>
      </n-grid>
    </Transition>
    <n-empty
      v-if="!loading && marketData && !getCatItems().length"
      description="No data for this category"
      size="small"
    />
    <n-empty
      v-if="!loading && !marketData && !error"
      description="No market data available"
      size="small"
    />

    <!-- Interactive bar chart -->
    <n-card title="涨跌幅一览" size="small" v-if="barData.length" class="chart-card">
      <template #header-extra>
        <div class="chart-actions">
          <n-button
            size="tiny"
            quaternary
            @click="resetZoom"
            :disabled="scale === 1 && panX === 0 && panY === 0"
          >Reset</n-button>
          <n-button size="tiny" quaternary @click="downloadChart">Download PNG</n-button>
        </div>
      </template>

      <div
        ref="chartContainer"
        class="chart-container"
        @wheel.prevent="onChartWheel"
        @mousedown="onChartMouseDown"
        @mousemove="onChartMouseMove"
        @mouseup="onChartMouseUp"
        @mouseleave="onChartMouseUp"
      >
        <svg
          ref="chartSvg"
          :viewBox="`0 0 ${SVG_W} ${SVG_H}`"
          class="chart-svg"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Background -->
          <rect x="0" y="0" :width="SVG_W" :height="SVG_H" fill="#fafbfc" rx="6" />

          <!-- Chart content group (transformed for zoom/pan) -->
          <g class="chart-inner" :transform="`translate(${panX}, ${panY}) scale(${scale})`">
            <!-- Grid lines -->
            <g v-for="(gl, idx) in yGridLines" :key="'gl'+idx">
              <line
                :x1="M.left" :y1="gl.y" :x2="M.left + INNER_W" :y2="gl.y"
                :stroke="gl.isZero ? '#d0d5dd' : '#e8eaed'"
                :stroke-width="gl.isZero ? 1.2 : 0.8"
                :stroke-dasharray="gl.isZero ? 'none' : '5,4'"
              />
              <text
                :x="M.left - 6" :y="gl.y + 3"
                text-anchor="end"
                font-size="10"
                fill="#8b919e"
                font-family="system-ui, sans-serif"
              >{{ gl.label }}</text>
            </g>

            <!-- Y-axis line -->
            <line :x1="M.left" :y1="M.top" :x2="M.left" :y2="M.top + INNER_H" stroke="#d0d5dd" stroke-width="1" />

            <!-- X-axis zero line -->
            <line :x1="M.left" :y1="ZERO_Y" :x2="M.left + INNER_W" :y2="ZERO_Y" stroke="#d0d5dd" stroke-width="1.2" />

            <!-- Bars -->
            <g
              v-for="(item, i) in barData"
              :key="item.symbol || i"
              @mouseenter="onBarEnter(item)"
              @mouseleave="onBarLeave"
              style="cursor:pointer"
            >
              <rect
                :x="barSlotX(i, barData.length)"
                :y="barYPos(item.changePct || 0)"
                :width="barWidthVal(barData.length)"
                :height="barHeightVal(item.changePct || 0)"
                :fill="barFill(item.changePct || 0)"
                :opacity="hoveredBar && hoveredBar.symbol === item.symbol ? 1 : 0.82"
                rx="3"
              />
              <!-- Percentage label above bar -->
              <text
                :x="barSlotX(i, barData.length) + barWidthVal(barData.length) / 2"
                :y="barYPos(item.changePct || 0) - 6"
                text-anchor="middle"
                font-size="9"
                :fill="barFill(item.changePct || 0)"
                font-family="system-ui, sans-serif"
                font-weight="500"
              >{{ (item.changePct || 0) >= 0 ? '+' : '' }}{{ (item.changePct || 0).toFixed(1) }}%</text>
              <!-- Symbol label below (angled) -->
              <text
                :x="barSlotX(i, barData.length) + barWidthVal(barData.length) / 2"
                :y="M.top + INNER_H + 16"
                text-anchor="end"
                font-size="9"
                fill="#667085"
                font-family="system-ui, sans-serif"
                :transform="`rotate(-35, ${barSlotX(i, barData.length) + barWidthVal(barData.length) / 2}, ${M.top + INNER_H + 16})`"
              >{{ item.symbol }}</text>
            </g>
          </g>

          <!-- Hint text (fixed position, not affected by zoom) -->
          <text
            :x="SVG_W / 2" y="14"
            text-anchor="middle" font-size="10" fill="#98a2b3"
            font-family="system-ui, sans-serif"
          >Drag to pan &bull; Scroll to zoom &bull; Hover bars for details</text>
        </svg>

        <!-- HTML tooltip overlay -->
        <Transition name="tip-fade">
          <div v-if="hoveredBar" class="chart-tooltip" :style="tooltipStyle">
            <div class="tip-symbol">{{ hoveredBar.symbol }}</div>
            <div class="tip-name">{{ hoveredBar.name }}</div>
            <div class="tip-price">
              {{ hoveredBar.price?.toLocaleString() }}
              <span v-if="hoveredBar.unit" class="tip-price-unit">{{ hoveredBar.unit }}</span>
            </div>
            <div
              class="tip-change"
              :style="{ color: (hoveredBar.changePct ?? 0) >= 0 ? '#f87171' : '#34d399' }"
            >
              {{ (hoveredBar.changePct ?? 0) >= 0 ? '+' : '' }}{{ hoveredBar.changePct?.toFixed(2) }}%
            </div>
          </div>
        </Transition>
      </div>
    </n-card>
  </div>
</template>

<style scoped>
/* ── Category pills ── */
.cat-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}
.cat-pill {
  padding: 6px 16px;
  border-radius: 20px;
  border: 1px solid #e0e0e0;
  background: #fff;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}
.cat-pill:hover {
  border-color: #bbb;
  color: #333;
  background: #f9f9f9;
}
.cat-pill.active {
  background: #1a1a2e;
  color: #fff;
  border-color: #1a1a2e;
  font-weight: 500;
}

/* ── Indicator cards ── */
.indicator-card {
  transition: box-shadow 0.2s;
}
.indicator-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-symbol {
  font-size: 11px;
  color: #999;
}
.card-source-link {
  font-size: 13px;
  color: #d97706;
  text-decoration: none;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(217, 119, 6, 0.08);
  transition: background 0.15s, color 0.15s;
  line-height: 1;
  position: relative;
  z-index: 10;
  pointer-events: auto;
}
.card-source-link:hover {
  background: #fef3c7;
  color: #b45309;
}
.card-price {
  font-size: 20px;
  font-weight: 600;
  margin-top: 2px;
}
.card-price-link {
  text-decoration: none;
  cursor: pointer;
  transition: opacity 0.15s, text-decoration 0.15s;
  position: relative;
  z-index: 10;
  pointer-events: auto;
}
.card-price-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}
.card-unit {
  font-size: 11px;
  color: #999;
  font-weight: 400;
  margin-left: 4px;
}
.card-change {
  font-size: 13px;
  font-weight: 500;
  margin-top: 2px;
}
.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: #bbb;
  margin-top: 2px;
}
.card-gran {
  background: #f5f5f5;
  padding: 1px 5px;
  border-radius: 3px;
}

/* ── Grid fade transition ── */
.grid-fade-enter-active,
.grid-fade-leave-active {
  transition: opacity 0.2s ease;
}
.grid-fade-enter-from,
.grid-fade-leave-to {
  opacity: 0;
}

/* ── Chart ── */
.chart-card {
  margin-top: 8px;
}
.chart-actions {
  display: flex;
  gap: 6px;
}
.chart-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  cursor: grab;
  user-select: none;
  border-radius: 8px;
  background: #fafbfc;
}
.chart-container:active {
  cursor: grabbing;
}
.chart-svg {
  display: block;
  width: 100%;
  height: auto;
  min-height: 320px;
}

/* ── Tooltip ── */
.chart-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(30, 30, 40, 0.92);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  z-index: 10;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
  transform: translateY(-100%);
  white-space: nowrap;
}
.tip-symbol {
  font-weight: 700;
  font-size: 13px;
}
.tip-name {
  opacity: 0.7;
  font-size: 11px;
}
.tip-price {
  font-weight: 600;
  margin-top: 2px;
}
.tip-price-unit {
  font-weight: 400;
  opacity: 0.7;
}
.tip-change {
  font-weight: 600;
  font-size: 13px;
  margin-top: 1px;
}

.tip-fade-enter-active,
.tip-fade-leave-active {
  transition: opacity 0.12s ease;
}
.tip-fade-enter-from,
.tip-fade-leave-to {
  opacity: 0;
}

/* ── Status messages ── */
.status-msg {
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
}
.status-msg.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}
</style>
