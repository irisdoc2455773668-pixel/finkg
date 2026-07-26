<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import api from '@/api/client'
import { NCard, NGrid, NGi, NStatistic, NTag, NButton, NEmpty } from 'naive-ui'

const store = useAppStore()
const router = useRouter()
const marketData = ref<any>(null)
const recentNews = ref<any[]>([])
const graphStats = ref<any>(null)
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    await store.fetchStatus()
  } catch (e) {
    console.error('Status fetch error:', e)
  }

  try {
    const [mkt, news, graph] = await Promise.all([
      api.get('/market/indicators').catch(() => ({ data: null })),
      api.get('/news', { params: { pageSize: 5 } }).catch(() => ({ data: { list: [] } })),
      api.get('/graph/stats').catch(() => ({ data: null })),
    ])
    marketData.value = mkt.data
    recentNews.value = news.data?.list || []
    graphStats.value = graph.data
  } catch (e: any) {
    console.error('Dashboard data fetch error:', e)
    error.value = 'Failed to load some dashboard data'
  } finally {
    loading.value = false
  }
})

// ── Stat card config with color accents ──
const statCards = [
  {
    key: 'articles',
    label: '资讯总量',
    accent: '#3b82f6',
    get value() { return store.status?.articleCount ?? 0 },
  },
  {
    key: 'analyzed',
    label: '已分析',
    accent: '#059669',
    get value() { return store.status?.analyzedCount ?? 0 },
  },
  {
    key: 'market',
    label: '市场指标',
    accent: '#d97706',
    get value() { return marketData.value?.total ?? 0 },
  },
  {
    key: 'nodes',
    label: '图谱节点',
    accent: '#7c3aed',
    get value() { return graphStats.value?.totalNodes ?? 0 },
  },
  {
    key: 'edges',
    label: '图谱关系',
    accent: '#ec4899',
    get value() { return graphStats.value?.totalEdges ?? 0 },
  },
]
</script>

<template>
  <div>
    <!-- Error banner -->
    <div v-if="error" class="error-banner">{{ error }}</div>

    <!-- Stats Row -->
    <n-grid :cols="5" :x-gap="12" style="margin-bottom:24px">
      <n-gi v-for="card in statCards" :key="card.key">
        <n-card size="small" class="stat-card" :style="{ borderLeftColor: card.accent }">
          <div class="stat-inner">
            <div class="stat-accent-dot" :style="{ background: card.accent }"></div>
            <n-statistic :label="card.label" :value="card.value" />
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid :cols="2" :x-gap="16">
      <!-- Market Overview -->
      <n-gi>
        <n-card title="市场概览" size="small">
          <div v-if="marketData?.categories">
            <div v-for="(items, cat) in marketData.categories" :key="cat" class="market-category">
              <div class="market-cat-header">
                <span class="market-cat-name">{{ cat }}</span>
                <n-button text size="tiny" @click="router.push('/market')" class="market-view-all">
                  View all &rarr;
                </n-button>
              </div>
              <div
                v-for="item in (items as any[]).slice(0, 3)"
                :key="item.symbol"
                class="market-row"
              >
                <span class="market-symbol-col">
                  <a
                    v-if="item.sourceUrl && item.sourceUrl.length"
                    :href="item.sourceUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="market-symbol-link"
                    :title="'Open data source: ' + item.sourceUrl"
                    @click.stop
                  >{{ item.symbol }} &#8599;</a>
                  <span v-else class="market-symbol-plain">{{ item.symbol }}</span>
                  <span class="market-name">{{ item.name }}</span>
                </span>
                <a
                  v-if="item.sourceUrl && item.sourceUrl.length"
                  :href="item.sourceUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="market-price-link"
                  :style="{ color: (item.changePct ?? 0) >= 0 ? '#dc2626' : '#059669' }"
                  :title="'View ' + item.symbol + ' on source'"
                  @click.stop
                >
                  {{ item.price?.toLocaleString() }}
                  <span class="market-change">
                    {{ (item.changePct ?? 0) >= 0 ? '+' : '' }}{{ item.changePct?.toFixed(2) }}%
                  </span>
                </a>
                <span
                  v-else
                  class="market-price-col"
                  :style="{ color: (item.changePct ?? 0) >= 0 ? '#dc2626' : '#059669' }"
                >
                  {{ item.price?.toLocaleString() }}
                  <span class="market-change">
                    {{ (item.changePct ?? 0) >= 0 ? '+' : '' }}{{ item.changePct?.toFixed(2) }}%
                  </span>
                </span>
              </div>
            </div>
          </div>
          <n-empty v-else-if="!loading" description="No market data" size="small" />
          <div v-else style="text-align:center;padding:20px;color:#999">Loading...</div>
        </n-card>
      </n-gi>

      <!-- Recent News -->
      <n-gi>
        <n-card title="最新资讯" size="small">
          <div v-if="recentNews.length">
            <div v-for="item in recentNews" :key="item.id" class="news-row">
              <div class="news-main">
                <n-tag
                  size="tiny"
                  :type="item.sentiment === 'bullish' ? 'error' : item.sentiment === 'bearish' ? 'success' : 'default'"
                  :bordered="false"
                >{{ item.sentiment || 'neutral' }}</n-tag>
                <span class="news-title">{{ item.title?.substring(0, 80) }}</span>
              </div>
              <span class="news-source">{{ item.sourceName }}</span>
            </div>
          </div>
          <n-empty v-else description="No news yet. Go fetch some from the News page." size="small">
            <template #extra>
              <n-button size="small" @click="router.push('/news')">Go fetch</n-button>
            </template>
          </n-empty>
          <n-button v-if="recentNews.length" text size="small" style="margin-top:8px" @click="router.push('/news')">
            View all &rarr;
          </n-button>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Top Entities -->
    <n-card title="核心实体" size="small" style="margin-top:16px" v-if="graphStats?.topEntities?.length">
      <div class="entity-cloud">
        <n-tag
          v-for="e in graphStats.topEntities.slice(0, 15)"
          :key="e.id"
          :bordered="false"
          size="small"
          class="entity-tag"
          :style="{
            background:
              e.type === 'Company'     ? 'rgba(59,130,246,0.1)' :
              e.type === 'Location'    ? 'rgba(5,150,105,0.1)'  :
              e.type === 'Person'      ? 'rgba(245,158,11,0.1)' :
              'rgba(217,119,6,0.1)',
          }"
        >{{ e.name }} ({{ e.mentions }})</n-tag>
      </div>
    </n-card>
  </div>
</template>

<style scoped>
/* ── Error banner ── */
.error-banner {
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}

/* ── Stat cards ── */
.stat-card {
  border-left: 3px solid transparent;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.stat-card:hover {
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}
.stat-inner {
  display: flex;
  align-items: center;
  gap: 10px;
}
.stat-accent-dot {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  opacity: 0.12;
  flex-shrink: 0;
}

/* ── Market rows ── */
.market-category {
  margin-bottom: 12px;
}
.market-cat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.market-cat-name {
  font-size: 12px;
  color: #999;
  font-weight: 500;
}
.market-view-all {
  font-size: 11px;
}
.market-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  padding: 3px 0;
}
.market-symbol-col {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.market-symbol-link {
  color: #2563eb;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 1px;
  transition: color 0.15s;
  position: relative;
  z-index: 10;
  pointer-events: auto;
}
.market-symbol-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}
.market-symbol-plain {
  color: #333;
  font-weight: 500;
}
.market-name {
  font-size: 10px;
  color: #bbb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.market-price-col {
  font-weight: 500;
  white-space: nowrap;
}
.market-price-link {
  font-weight: 500;
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
  transition: opacity 0.15s, text-decoration 0.15s;
  position: relative;
  z-index: 10;
  pointer-events: auto;
}
.market-price-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}
.market-change {
  font-size: 11px;
  margin-left: 6px;
  font-weight: 400;
}

/* ── News rows ── */
.news-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f2f2f2;
  font-size: 13px;
}
.news-row:last-child {
  border-bottom: none;
}
.news-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.news-title {
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.news-source {
  font-size: 11px;
  color: #999;
  flex-shrink: 0;
  margin-left: 8px;
}

/* ── Entity cloud ── */
.entity-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.entity-tag {
  cursor: default;
}
</style>
