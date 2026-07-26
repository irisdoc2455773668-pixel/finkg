<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import api from '@/api/client'
import { NCard, NTag, NEmpty, NButton } from 'naive-ui'

// ── Constants ──
const NODE_COLORS: Record<string, string> = {
  Company: '#3b82f6',
  Location: '#059669',
  FinanceTerm: '#d97706',
  Topic: '#8b5cf6',
  EventCluster: '#ec4899',
  Article: '#9ca3af',
  Person: '#f59e0b',
}

const NODE_LABELS: Record<string, string> = {
  Company: '公司',
  Location: '地点',
  FinanceTerm: '金融术语',
  Topic: '主题',
  EventCluster: '事件',
  Article: '文章',
  Person: '人物',
}

const ALL_NODE_TYPES = ['Company', 'Location', 'FinanceTerm', 'Topic', 'Person', 'EventCluster', 'Article']
const NODE_COUNT_OPTIONS = [30, 50, 80, 120]
const CATEGORY_ORDER = ['Company', 'Location', 'FinanceTerm', 'Topic', 'Person', 'EventCluster', 'Other']

// ── State ──
const graphData = ref<any>(null)
const stats = ref<any>(null)
const selectedNode = ref<any>(null)
const nodeArticles = ref<any[]>([])
const loading = ref(false)
const error = ref('')

// ── Filter state ──
const filterNodeTypes = ref<string[]>(['Company', 'Location', 'FinanceTerm'])
const maxNodesCount = ref(50)
const expandedCategories = ref<Set<string>>(new Set(['Company']))

// ── Force simulation state ──
const svgWidth = ref(1200)
const svgHeight = ref(750)
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
let animationId = 0

// ── Zoom / Pan state ──
const graphContainer = ref<HTMLElement | null>(null)
const graphSvg = ref<SVGSVGElement | null>(null)
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
const panStartX = ref(0)
const panStartY = ref(0)

// ── Tooltip state ──
const tooltipNode = ref<any>(null)
const tooltipX = ref(0)
const tooltipY = ref(0)

// ── Fetch data ──
onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const [g, s] = await Promise.all([
      api.get('/graph/visual', { params: { maxNodes: 200 } }),
      api.get('/graph/stats'),
    ])
    graphData.value = g.data
    stats.value = s.data
    initForceGraph()
  } catch (e: any) {
    console.error('Graph load error:', e)
    error.value = e?.response?.data?.detail || e?.message || 'Failed to load graph data'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
})

// ── Derived data ──
const rawNodes = computed(() => graphData.value?.nodes || [])
const rawEdges = computed(() => graphData.value?.edges || [])

const displayNodeData = computed(() => {
  return rawNodes.value
    .filter((n: any) => filterNodeTypes.value.includes(n.nodeType))
    .slice(0, maxNodesCount.value)
})

// ── Top 10 entities for bar chart ──
interface EntityItem {
  id: string
  name: string
  type: string
  mentions: number
  importance: number
  degree: number
}

const top10Entities = computed<EntityItem[]>(() => {
  const entities = (stats.value?.topEntities || []) as EntityItem[]
  return [...entities]
    .sort((a, b) => (b.mentions || b.degree || 0) - (a.mentions || a.degree || 0))
    .slice(0, 10)
})

const barChartMax = computed(() => {
  if (top10Entities.value.length === 0) return 1
  const max = Math.max(...top10Entities.value.map(e => e.mentions || e.degree || 0))
  return max || 1
})

// ── Bar chart dimensions (viewBox) ──
const barChartVB = { w: 400, h: 290 }
// layout: name right-aligned at x=78, bar at x=82, count at x=barEnd+6
const barChartNameX = 78
const barChartBarX = 84
const barChartBarMaxW = 240
const barRowH = 24
const barH = 17
const barTopPad = 10

// ── Categorized entities with expand/collapse ──
const categorizedEntities = computed<Record<string, EntityItem[]>>(() => {
  const entities: EntityItem[] = stats.value?.topEntities || []
  const grouped: Record<string, EntityItem[]> = {}
  for (const e of entities) {
    const key = e.type || 'Other'
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(e)
  }
  return grouped
})

const sortedCategories = computed(() => {
  const cats = Object.keys(categorizedEntities.value)
  return cats.sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a)
    const ib = CATEGORY_ORDER.indexOf(b)
    if (ia === -1 && ib === -1) return a.localeCompare(b)
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })
})

function toggleCategory(cat: string) {
  const next = new Set(expandedCategories.value)
  if (next.has(cat)) {
    next.delete(cat)
  } else {
    next.add(cat)
  }
  expandedCategories.value = next
}

// ── Force simulation ──
function initForceGraph() {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = 0
  }

  const rawNd = displayNodeData.value
  if (!rawNd.length) {
    nodes.value = []
    edges.value = []
    return
  }

  const nodeIds = new Set(rawNd.map((n: any) => n.id))

  const simNodes = rawNd.map((n: any) => ({
    ...n,
    x: Math.random() * svgWidth.value * 0.7 + svgWidth.value * 0.15,
    y: Math.random() * svgHeight.value * 0.7 + svgHeight.value * 0.15,
    vx: 0,
    vy: 0,
  }))

  const simEdges = rawEdges.value
    .filter((e: any) => nodeIds.has(e.sourceNodeId) && nodeIds.has(e.targetNodeId))
    .slice(0, 250)

  nodes.value = simNodes
  edges.value = simEdges

  // Type-based cluster centers
  const centers: Record<string, { x: number; y: number }> = {
    Company: { x: svgWidth.value * 0.25, y: svgHeight.value * 0.22 },
    Location: { x: svgWidth.value * 0.75, y: svgHeight.value * 0.22 },
    FinanceTerm: { x: svgWidth.value * 0.50, y: svgHeight.value * 0.50 },
    Topic: { x: svgWidth.value * 0.25, y: svgHeight.value * 0.78 },
    EventCluster: { x: svgWidth.value * 0.75, y: svgHeight.value * 0.78 },
    Article: { x: svgWidth.value * 0.50, y: svgHeight.value * 0.08 },
    Person: { x: svgWidth.value * 0.88, y: svgHeight.value * 0.50 },
  }

  function tick() {
    for (const n of simNodes) {
      const c = centers[n.nodeType] || { x: svgWidth.value * 0.5, y: svgHeight.value * 0.5 }
      n.vx += (c.x - n.x) * 0.002
      n.vy += (c.y - n.y) * 0.002
      n.vx *= 0.93
      n.vy *= 0.93
      const margin = 40
      if (n.x < margin) { n.x = margin; n.vx *= -0.5 }
      if (n.x > svgWidth.value - margin) { n.x = svgWidth.value - margin; n.vx *= -0.5 }
      if (n.y < margin) { n.y = margin; n.vy *= -0.5 }
      if (n.y > svgHeight.value - margin) { n.y = svgHeight.value - margin; n.vy *= -0.5 }
    }

    // Edge spring forces
    for (const e of simEdges) {
      const src = simNodes.find(n => n.id === e.sourceNodeId)
      const tgt = simNodes.find(n => n.id === e.targetNodeId)
      if (!src || !tgt) continue
      const dx = tgt.x - src.x
      const dy = tgt.y - src.y
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const restLen = 110
      const force = (dist - restLen) * 0.0006 * (e.weight || 0.5)
      const fx = (dx / dist) * force
      const fy = (dy / dist) * force
      src.vx += fx; src.vy += fy
      tgt.vx -= fx; tgt.vy -= fy
    }

    // Node repulsion
    for (let i = 0; i < simNodes.length; i++) {
      for (let j = i + 1; j < simNodes.length; j++) {
        const dx = simNodes[j].x - simNodes[i].x
        const dy = simNodes[j].y - simNodes[i].y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const minDist = 80
        if (dist < minDist) {
          const force = (minDist - dist) * 0.015
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          simNodes[i].vx -= fx; simNodes[i].vy -= fy
          simNodes[j].vx += fx; simNodes[j].vy += fy
        }
      }
    }

    for (const n of simNodes) {
      n.x += n.vx
      n.y += n.vy
    }
    nodes.value = [...simNodes]
    animationId = requestAnimationFrame(tick)
  }
  tick()
}

// Watch filters -> re-init graph
watch([filterNodeTypes, maxNodesCount], () => {
  initForceGraph()
}, { deep: true })

// ── Edge path ──
function edgePath(e: any): string {
  const src = nodes.value.find(n => n.id === e.sourceNodeId)
  const tgt = nodes.value.find(n => n.id === e.targetNodeId)
  if (!src || !tgt) return ''
  const mx = (src.x + tgt.x) / 2
  const my = (src.y + tgt.y) / 2
  const dx = tgt.x - src.x
  const dy = tgt.y - src.y
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  const curve = Math.min(len * 0.2, 55)
  const px = -dy / len * curve
  const py = dx / len * curve
  return `M ${src.x} ${src.y} Q ${mx + px} ${my + py} ${tgt.x} ${tgt.y}`
}

// ── Helpers ──
function nodeColor(type: string): string {
  return NODE_COLORS[type] || '#9ca3af'
}

function nodeLabel(type: string): string {
  return NODE_LABELS[type] || type
}

function nodeRadius(n: any): number {
  return 5 + Math.log2((n.mentionCount || 1) + 1) * 3.5
}

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.substring(0, max) + '...' : s
}

// ── Node click ──
async function selectNode(n: any) {
  selectedNode.value = n
  nodeArticles.value = []
  try {
    const { data } = await api.get(`/graph/nodes/${n.id}`)
    nodeArticles.value = data.articles || []
  } catch (e) {
    console.error('Node articles fetch error:', e)
    nodeArticles.value = []
  }
}

// ── Tooltip ──
function onNodeEnter(n: any) {
  if (isPanning.value) return
  tooltipNode.value = n
}
function onNodeLeave() {
  tooltipNode.value = null
}

const tooltipStyle = computed(() => ({
  left: `${tooltipX.value + 14}px`,
  top: `${tooltipY.value - 10}px`,
}))

// ── Zoom / Pan ──
function onGraphWheel(e: WheelEvent) {
  e.preventDefault()
  const rect = graphContainer.value?.getBoundingClientRect()
  if (!rect) return
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const factor = e.deltaY > 0 ? 0.9 : 1.1
  const newZoom = Math.min(5, Math.max(0.2, zoom.value * factor))
  panX.value = mx - (mx - panX.value) * (newZoom / zoom.value)
  panY.value = my - (my - panY.value) * (newZoom / zoom.value)
  zoom.value = newZoom
}

function onGraphMouseDown(e: MouseEvent) {
  isPanning.value = true
  panStartX.value = e.clientX - panX.value
  panStartY.value = e.clientY - panY.value
}

function onGraphMouseMove(e: MouseEvent) {
  const rect = graphContainer.value?.getBoundingClientRect()
  if (!rect) return
  tooltipX.value = e.clientX - rect.left
  tooltipY.value = e.clientY - rect.top
  if (isPanning.value) {
    panX.value = e.clientX - panStartX.value
    panY.value = e.clientY - panStartY.value
  }
}

function onGraphMouseUp() {
  isPanning.value = false
}

function resetGraphView() {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

// ── Download ──
function downloadGraph() {
  const svgEl = graphSvg.value
  if (!svgEl) return
  try {
    const clone = svgEl.cloneNode(true) as SVGSVGElement
    clone.setAttribute('width', String(svgWidth.value))
    clone.setAttribute('height', String(svgHeight.value))
    const inner = clone.querySelector('g.graph-inner')
    if (inner) inner.setAttribute('transform', 'translate(0,0) scale(1)')
    const svgStr = new XMLSerializer().serializeToString(clone)
    const canvas = document.createElement('canvas')
    const dpr = 2
    canvas.width = svgWidth.value * dpr
    canvas.height = svgHeight.value * dpr
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#fafaf7'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    const img = new Image()
    const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    img.onload = () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      const a = document.createElement('a')
      a.download = `knowledge-graph-${new Date().toISOString().slice(0, 10)}.png`
      a.href = canvas.toDataURL('image/png')
      a.click()
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      console.error('Failed to render graph SVG for download')
    }
    img.src = url
  } catch (e) {
    console.error('Download graph error:', e)
  }
}
</script>

<template>
  <div class="graph-page">
    <!-- Error banner -->
    <div
      v-if="error"
      class="error-banner"
    >
      {{ error }}
    </div>

    <!-- Two-column layout -->
    <div class="graph-layout">
      <!-- ========== LEFT COLUMN (40%) ========== -->
      <div class="graph-left">
        <!-- Stats card -->
        <n-card title="图谱统计" size="small">
          <div v-if="stats" class="stats-panel">
            <div class="stat-summary">
              <div>总节点: <strong>{{ stats.totalNodes }}</strong></div>
              <div>总关系: <strong>{{ stats.totalEdges }}</strong></div>
            </div>

            <!-- Node type distribution -->
            <div class="stat-section-title">节点类型分布</div>
            <div v-for="(count, type) in stats.nodeTypes" :key="type" class="stat-type-row">
              <span class="type-dot" :style="{ background: nodeColor(String(type)) }"></span>
              <span class="type-name">{{ nodeLabel(String(type)) }}</span>
              <span class="type-count">{{ count }}</span>
            </div>
          </div>
          <n-empty v-else-if="!loading" description="暂无数据" size="small" />
          <div v-if="loading" class="loading-text">加载中...</div>
        </n-card>

        <!-- SVG Bar Chart: Top 10 entities -->
        <n-card title="Top 10 核心实体" size="small" style="margin-top: 12px">
          <div v-if="top10Entities.length > 0" class="bar-chart-wrap">
            <svg
              class="bar-chart-svg"
              :viewBox="`0 0 ${barChartVB.w} ${barChartVB.h}`"
              xmlns="http://www.w3.org/2000/svg"
            >
              <g v-for="(e, idx) in top10Entities" :key="e.id">
                <!-- Row background on hover area -->
                <rect
                  :x="0"
                  :y="barTopPad + idx * barRowH"
                  :width="barChartVB.w"
                  :height="barRowH"
                  fill="transparent"
                />
                <!-- Type dot -->
                <circle
                  :cx="10"
                  :cy="barTopPad + idx * barRowH + barRowH / 2"
                  r="5"
                  :fill="nodeColor(e.type)"
                />
                <!-- Entity name (right-aligned before bar) -->
                <text
                  :x="barChartNameX"
                  :y="barTopPad + idx * barRowH + barRowH / 2 + 4"
                  text-anchor="end"
                  font-size="11"
                  fill="#334155"
                  font-family="'Inter', system-ui, -apple-system, sans-serif"
                >
                  {{ truncate(e.name, 11) }}
                </text>
                <!-- Bar -->
                <rect
                  :x="barChartBarX"
                  :y="barTopPad + idx * barRowH + (barRowH - barH) / 2"
                  :width="Math.max(((e.mentions || e.degree || 0) / barChartMax) * barChartBarMaxW, 3)"
                  :height="barH"
                  :fill="nodeColor(e.type)"
                  rx="3"
                  :opacity="0.82"
                />
                <!-- Count -->
                <text
                  :x="barChartBarX + Math.max(((e.mentions || e.degree || 0) / barChartMax) * barChartBarMaxW, 3) + 6"
                  :y="barTopPad + idx * barRowH + barRowH / 2 + 4"
                  font-size="11"
                  font-weight="600"
                  :fill="nodeColor(e.type)"
                  font-family="'Inter', system-ui, -apple-system, sans-serif"
                >
                  {{ e.mentions || e.degree || 0 }}
                </text>
              </g>
            </svg>
          </div>
          <div v-else-if="!loading" style="font-size:12px;color:#999;text-align:center;padding:16px 0">
            暂无核心实体数据
          </div>
          <div v-if="loading" class="loading-text">加载中...</div>
        </n-card>

        <!-- Collapsible categorized entities -->
        <n-card title="全部核心实体" size="small" style="margin-top: 12px">
          <div v-if="stats && sortedCategories.length > 0">
            <div v-for="cat in sortedCategories" :key="cat" class="entity-category">
              <div class="entity-cat-header" @click="toggleCategory(cat)">
                <span class="cat-chevron">{{ expandedCategories.has(cat) ? '▼' : '▶' }}</span>
                <span class="type-dot" :style="{ background: nodeColor(cat) }"></span>
                <span class="entity-cat-label">{{ nodeLabel(cat) }}</span>
                <span class="cat-count">({{ categorizedEntities[cat]?.length || 0 }})</span>
              </div>
              <div v-if="expandedCategories.has(cat)" class="entity-cat-body">
                <div
                  v-for="e in categorizedEntities[cat]"
                  :key="e.id"
                  class="top-entity"
                  :class="{ active: selectedNode?.id === e.id }"
                  @click="selectNode({ id: e.id, name: e.name, nodeType: e.type, mentionCount: e.mentions })"
                >
                  <span class="entity-name">{{ truncate(e.name, 18) }}</span>
                  <span class="entity-degree">{{ e.degree }}</span>
                </div>
              </div>
            </div>
          </div>
          <n-empty v-else-if="!loading" description="暂无数据" size="small" />
          <div v-if="loading" class="loading-text">加载中...</div>
        </n-card>
      </div>

      <!-- ========== RIGHT COLUMN (60%) ========== -->
      <div class="graph-right">
        <!-- Filter bar -->
        <n-card size="small" class="filter-card">
          <div class="filter-bar">
            <div class="filter-types">
              <label
                v-for="t in ALL_NODE_TYPES"
                :key="t"
                class="filter-checkbox"
              >
                <input
                  type="checkbox"
                  :value="t"
                  v-model="filterNodeTypes"
                  class="filter-input"
                />
                <span class="type-dot" :style="{ background: nodeColor(t) }"></span>
                <span class="filter-label">{{ nodeLabel(t) }}</span>
              </label>
            </div>
            <div class="filter-count">
              <span class="filter-count-label">显示节点数:</span>
              <button
                v-for="c in NODE_COUNT_OPTIONS"
                :key="c"
                class="count-btn"
                :class="{ active: maxNodesCount === c }"
                @click="maxNodesCount = c"
              >{{ c }}</button>
            </div>
          </div>
        </n-card>

        <!-- Graph card -->
        <n-card title="知识图谱" size="small" class="graph-card" style="margin-top: 12px">
          <template #header-extra>
            <div class="graph-actions">
              <n-button size="tiny" quaternary @click="resetGraphView" :disabled="zoom === 1 && panX === 0 && panY === 0">
                Reset
              </n-button>
              <n-button size="tiny" quaternary @click="downloadGraph">
                Download PNG
              </n-button>
            </div>
          </template>

          <div v-if="loading" class="loading-text" style="padding: 60px 0">Loading graph...</div>
          <n-empty v-else-if="!nodes.length" description="No graph data. Select node types above or run analysis first." size="small" />

          <div
            v-else
            ref="graphContainer"
            class="graph-container"
            @wheel.prevent="onGraphWheel"
            @mousedown="onGraphMouseDown"
            @mousemove="onGraphMouseMove"
            @mouseup="onGraphMouseUp"
            @mouseleave="onGraphMouseUp"
          >
            <svg
              ref="graphSvg"
              :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
              class="graph-svg"
              xmlns="http://www.w3.org/2000/svg"
            >
              <!-- Background -->
              <rect x="0" y="0" :width="svgWidth" :height="svgHeight" fill="#fafaf8" rx="8" />

              <!-- Transformed graph group -->
              <g class="graph-inner" :transform="`translate(${panX}, ${panY}) scale(${zoom})`">
                <!-- Curved edges -->
                <path
                  v-for="e in edges"
                  :key="e.sourceNodeId + '-' + e.targetNodeId"
                  :d="edgePath(e)"
                  fill="none"
                  stroke="#d5d8de"
                  :stroke-width="0.5 + (e.weight || 0.2) * 0.5"
                  :opacity="(e.weight || 0.3) * 0.55"
                />

                <!-- Nodes -->
                <g
                  v-for="n in nodes"
                  :key="n.id"
                  @click="selectNode(n)"
                  @mouseenter="onNodeEnter(n)"
                  @mouseleave="onNodeLeave"
                  style="cursor: pointer"
                >
                  <!-- Glow for hovered -->
                  <circle
                    v-if="tooltipNode?.id === n.id"
                    :cx="n.x"
                    :cy="n.y"
                    :r="nodeRadius(n) + 4"
                    :fill="nodeColor(n.nodeType)"
                    opacity="0.15"
                  />
                  <!-- Main circle -->
                  <circle
                    :cx="n.x"
                    :cy="n.y"
                    :r="nodeRadius(n)"
                    :fill="nodeColor(n.nodeType)"
                    :opacity="selectedNode?.id === n.id ? 1 : 0.85"
                    :stroke="selectedNode?.id === n.id ? '#1e1e2e' : tooltipNode?.id === n.id ? '#555' : 'none'"
                    :stroke-width="selectedNode?.id === n.id ? 2.5 : tooltipNode?.id === n.id ? 1.5 : 0"
                  />
                  <!-- Label -->
                  <text
                    :x="n.x + nodeRadius(n) + 4"
                    :y="n.y + 4"
                    font-size="10"
                    :fill="selectedNode?.id === n.id ? '#111' : '#667085'"
                    font-family="'Inter', system-ui, -apple-system, sans-serif"
                    style="pointer-events: none"
                  >
                    {{ truncate(n.name, 16) }}
                  </text>
                </g>
              </g>

              <!-- Legend (fixed, bottom-left) -->
              <g class="graph-legend" transform="translate(14, 718)">
                <rect x="0" y="-14" width="360" height="38" rx="6" fill="rgba(30,30,40,0.88)" />
                <g v-for="(color, type, idx) in NODE_COLORS" :key="type" :transform="`translate(${12 + idx * 48}, 0)`">
                  <circle cx="4" cy="4" r="5" :fill="color" />
                  <text x="12" y="7" font-size="10" fill="#ddd" font-family="'Inter', system-ui, -apple-system, sans-serif">{{ nodeLabel(type) }}</text>
                </g>
              </g>

              <!-- Hint text (fixed, top-center) -->
              <text :x="svgWidth / 2" y="16" text-anchor="middle" font-size="10" fill="#bbb" font-family="'Inter', system-ui, -apple-system, sans-serif">
                Drag to pan &bull; Scroll to zoom &bull; Click nodes for details
              </text>
            </svg>

            <!-- HTML tooltip -->
            <Transition name="tip-fade">
              <div
                v-if="tooltipNode && !isPanning"
                class="graph-tooltip"
                :style="tooltipStyle"
              >
                <div class="gt-name">{{ tooltipNode.name }}</div>
                <div class="gt-row">
                  <span class="type-dot" :style="{ background: nodeColor(tooltipNode.nodeType), display: 'inline-block' }"></span>
                  <span>{{ tooltipNode.nodeType }}</span>
                </div>
                <div class="gt-row">Mentions: <strong>{{ tooltipNode.mentionCount ?? 0 }}</strong></div>
              </div>
            </Transition>
          </div>
        </n-card>

        <!-- Node detail panel -->
        <n-card v-if="selectedNode" title="节点详情" size="small" style="margin-top: 12px">
          <div class="detail-header">
            <span class="type-dot" :style="{ background: nodeColor(selectedNode.nodeType) }"></span>
            <strong>{{ selectedNode.name }}</strong>
            <n-tag size="tiny" :bordered="false" :color="{ color: nodeColor(selectedNode.nodeType), textColor: '#fff' }">{{ selectedNode.nodeType }}</n-tag>
            <span class="detail-mentions">Mentioned {{ selectedNode.mentionCount }} times</span>
          </div>
          <div v-if="nodeArticles.length" class="detail-articles">
            <div class="detail-section-label">Related Articles:</div>
            <div v-for="a in nodeArticles.slice(0, 10)" :key="a.id" class="detail-article-row">
              <a :href="a.url" target="_blank" rel="noopener">{{ a.title?.substring(0, 80) }}</a>
            </div>
          </div>
          <div v-else style="font-size: 12px; color: #999; margin-top: 8px">No related articles found.</div>
        </n-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Layout ── */
.graph-page {
  min-height: 100%;
}

.error-banner {
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.graph-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.graph-left {
  flex: 0 0 38%;
  min-width: 280px;
  max-width: 420px;
}

.graph-right {
  flex: 1 1 62%;
  min-width: 0;
}

@media (max-width: 900px) {
  .graph-layout {
    flex-direction: column;
  }
  .graph-left {
    flex: 1 1 auto;
    max-width: none;
  }
  .graph-right {
    flex: 1 1 auto;
  }
}

/* ── Stats panel ── */
.stats-panel {
  font-size: 12px;
}
.stat-summary {
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.8;
}
.stat-section-title {
  font-size: 11px;
  color: #999;
  margin-bottom: 8px;
  margin-top: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.stat-type-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  font-size: 12px;
}
.type-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.type-name {
  font-size: 12px;
  color: #555;
}
.type-count {
  margin-left: auto;
  color: #999;
  font-weight: 600;
  font-size: 11px;
}

/* ── Bar chart ── */
.bar-chart-wrap {
  width: 100%;
}
.bar-chart-svg {
  display: block;
  width: 100%;
  height: auto;
}

/* ── Collapsible categories ── */
.entity-category {
  margin-bottom: 6px;
}
.entity-cat-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  font-size: 12px;
  font-weight: 600;
  color: #555;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.12s;
  user-select: none;
}
.entity-cat-header:hover {
  background: #f0f0f5;
}
.cat-chevron {
  font-size: 9px;
  color: #999;
  width: 12px;
  text-align: center;
  flex-shrink: 0;
}
.entity-cat-label {
  font-size: 11px;
  color: #666;
}
.cat-count {
  font-size: 10px;
  color: #aaa;
  margin-left: auto;
}
.entity-cat-body {
  padding-left: 6px;
}

.top-entity {
  font-size: 11px;
  padding: 4px 8px 4px 22px;
  cursor: pointer;
  color: #555;
  border-radius: 4px;
  transition: background 0.15s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.top-entity:hover {
  background: #f0f0f5;
}
.top-entity.active {
  background: #eef2ff;
  color: #3730a3;
}
.entity-name {
  font-size: 12px;
  font-weight: 500;
}
.entity-degree {
  color: #999;
  font-size: 10px;
  background: #f3f3f8;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 500;
}

/* ── Filter bar ── */
.filter-card :deep(.n-card__content) {
  padding: 10px 16px;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.filter-types {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.filter-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #555;
  user-select: none;
}
.filter-input {
  margin: 0;
  accent-color: #3b82f6;
  cursor: pointer;
}
.filter-label {
  font-size: 11px;
}
.filter-count {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}
.filter-count-label {
  font-size: 11px;
  color: #999;
  margin-right: 2px;
}
.count-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid #dde;
  border-radius: 4px;
  background: #fff;
  color: #666;
  cursor: pointer;
  transition: all 0.12s;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
.count-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}
.count-btn.active {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

/* ── Graph ── */
.graph-card :deep(.n-card__content) {
  padding: 0;
}
.graph-actions {
  display: flex;
  gap: 6px;
}
.graph-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  cursor: grab;
  user-select: none;
  border-radius: 0 0 8px 8px;
  background: #fafaf8;
}
.graph-container:active {
  cursor: grabbing;
}
.graph-svg {
  display: block;
  width: 100%;
  height: 600px;
}

/* ── Tooltip ── */
.graph-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(30, 30, 40, 0.92);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  z-index: 10;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
  transform: translateY(-100%);
  white-space: nowrap;
}
.gt-name {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 2px;
}
.gt-row {
  font-size: 11px;
  opacity: 0.85;
  display: flex;
  align-items: center;
  gap: 5px;
}

.tip-fade-enter-active,
.tip-fade-leave-active {
  transition: opacity 0.1s ease;
}
.tip-fade-enter-from,
.tip-fade-leave-to {
  opacity: 0;
}

/* ── Node detail ── */
.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.detail-mentions {
  color: #999;
  font-size: 11px;
}
.detail-articles {
  margin-top: 10px;
}
.detail-section-label {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
  font-weight: 600;
}
.detail-article-row {
  padding: 3px 0;
  font-size: 12px;
}
.detail-article-row a {
  color: #333;
  text-decoration: none;
}
.detail-article-row a:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* ── Shared ── */
.loading-text {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}
</style>
