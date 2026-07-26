<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import api from '@/api/client'
import { NCard, NTag, NPagination, NSpace, NSelect, NInput, NEmpty, NModal, NButton, NPopconfirm, useMessage } from 'naive-ui'

const store = useAppStore()
const message = useMessage()
const articles = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const crawlingNews = ref(false)
const crawlingFull = ref(false)
const selectedArticle = ref<any>(null)
const showDetail = ref(false)
const searchQuery = ref('')
const deletingId = ref<string | null>(null)

const filters = ref({ category: '', sentiment: '', source: '', riskLevel: '', region: '' })

const categoryOptions = [
  { label: '全部类别', value: '' },
  { label: '经济', value: 'economy' }, { label: '政治', value: 'politics' },
  { label: '商业', value: 'business' }, { label: '科技', value: 'technology' },
  { label: '社会', value: 'society' }, { label: '文化', value: 'culture' },
]
const regionOptions = [
  { label: '全部地区', value: '' },
  { label: '中国', value: 'cn' }, { label: '美国', value: 'us' },
  { label: '欧洲', value: 'eu' }, { label: '香港', value: 'hk' },
  { label: '日本', value: 'jp' },
]
const sentimentOptions = [
  { label: '全部情绪', value: '' },
  { label: '看涨', value: 'bullish' }, { label: '看跌', value: 'bearish' }, { label: '中性', value: 'neutral' },
]

// ── Client-side search filtering ──
const filteredArticles = computed(() => {
  if (!searchQuery.value.trim()) return articles.value
  const q = searchQuery.value.trim().toLowerCase()
  return articles.value.filter((item: any) => {
    const title = (item.title || '').toLowerCase()
    const summary = (item.summary || '').toLowerCase()
    return title.includes(q) || summary.includes(q)
  })
})

async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, pageSize: pageSize.value }
    if (filters.value.category) params.category = filters.value.category
    if (filters.value.sentiment) params.sentiment = filters.value.sentiment
    if (filters.value.riskLevel) params.riskLevel = filters.value.riskLevel
    if (filters.value.region) params.region = filters.value.region
    params.dateFrom = store.dateFrom
    params.dateTo = store.dateTo
    const { data } = await api.get('/news', { params })
    articles.value = data.list || []
    total.value = data.total || 0
  } catch (e) {
    console.error(e)
    message.error('加载资讯列表失败')
  } finally {
    loading.value = false
  }
}

async function triggerCrawl() {
  crawlingNews.value = true
  try {
    await api.post('/pipeline/crawl/news', null, {
      params: { date_from: store.dateFrom, date_to: store.dateTo },
    })
    message.success('新闻抓取已启动，正在后台抓取...')
    const check = setInterval(async () => {
      try {
        const { data: status } = await api.get('/pipeline/status')
        if (!status.crawl?.active) {
          clearInterval(check)
          crawlingNews.value = false
          await load()
          await store.fetchStatus()
          message.success('新闻抓取完成！')
        }
      } catch {
        // Retry polling
      }
    }, 2000)
  } catch (e: any) {
    message.error('抓取失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    crawlingNews.value = false
  }
}

async function triggerFullPipeline() {
  crawlingFull.value = true
  try {
    await api.post('/pipeline/full', null, {
      params: { date_from: store.dateFrom, date_to: store.dateTo },
    })
    message.success('全流程已启动（抓取 -> 分析 -> 报告）')
    const check = setInterval(async () => {
      try {
        const { data: status } = await api.get('/pipeline/status')
        if (!status.crawl?.active && !status.pipeline?.active) {
          clearInterval(check)
          crawlingFull.value = false
          await load()
          await store.fetchStatus()
          message.success('全流程完成！可查看报告页面')
        }
      } catch {
        // Retry polling
      }
    }, 3000)
  } catch (e: any) {
    message.error('启动失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    crawlingFull.value = false
  }
}

async function openDetail(article: any) {
  try {
    const { data } = await api.get(`/news/${article.id}`)
    selectedArticle.value = data.article
    showDetail.value = true
  } catch {
    message.error('加载文章详情失败')
  }
}

async function deleteArticle(article: any) {
  deletingId.value = article.id
  try {
    await api.delete(`/news/${article.id}`)
    articles.value = articles.value.filter((a: any) => a.id !== article.id)
    total.value = Math.max(0, total.value - 1)
    message.success('文章已删除')
    // Refresh store counts
    await store.fetchStatus()
  } catch (e: any) {
    message.error('删除失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    deletingId.value = null
  }
}

watch(() => store.dateRange, load)
watch(filters, () => { page.value = 1; load() }, { deep: true })
onMounted(load)

function onPageChange(p: number) { page.value = p; load() }
</script>

<template>
  <div>
    <!-- Action Bar -->
    <n-space style="margin-bottom:16px" justify="space-between">
      <n-space>
        <n-button type="primary" @click="triggerCrawl"
                  :loading="crawlingNews" :disabled="crawlingNews || crawlingFull">
          {{ crawlingNews ? '抓取中...' : '抓取新闻' }}
        </n-button>
        <n-button @click="triggerFullPipeline"
                  :loading="crawlingFull" :disabled="crawlingNews || crawlingFull">
          {{ crawlingFull ? '全流程运行中...' : '全流程（抓取+分析+报告）' }}
        </n-button>
      </n-space>
      <n-space>
        <span style="font-size:12px;color:#999">共 {{ total }} 篇资讯</span>
        <n-button size="small" @click="load" :loading="loading">刷新列表</n-button>
      </n-space>
    </n-space>

    <!-- Search + Filters Row -->
    <n-space style="margin-bottom:16px" align="center" :wrap="true">
      <n-input
        v-model:value="searchQuery"
        placeholder="搜索标题或摘要..."
        size="small"
        style="width:220px"
        clearable
      >
        <template #prefix>
          <span style="font-size:13px;color:#999">&#128269;</span>
        </template>
      </n-input>
      <span style="color:#ddd;font-size:12px">|</span>
      <n-select v-model:value="filters.category" :options="categoryOptions" size="small" style="width:110px" />
      <n-select v-model:value="filters.region" :options="regionOptions" size="small" style="width:110px" />
      <n-select v-model:value="filters.sentiment" :options="sentimentOptions" size="small" style="width:110px" />
      <n-input v-model:value="filters.source" placeholder="搜索来源..." size="small" style="width:130px" clearable />
    </n-space>

    <!-- Articles -->
    <n-card size="small">
      <!-- Loading state -->
      <div v-if="loading" style="text-align:center;padding:40px;color:#999">加载中...</div>

      <!-- Empty: no data at all -->
      <n-empty v-else-if="!articles.length"
               description="暂无资讯数据。点击上方「抓取新闻」按钮获取最新财经资讯，或调整时间范围后重试。">
        <template #extra>
          <n-button type="primary" size="small" @click="triggerCrawl"
                    :loading="crawlingNews" :disabled="crawlingNews || crawlingFull">
            开始抓取
          </n-button>
        </template>
      </n-empty>

      <!-- Empty: search/filter returned no results -->
      <n-empty
        v-else-if="!filteredArticles.length && searchQuery"
        description="没有匹配的搜索结果，请尝试其他关键词"
        size="small"
      >
        <template #extra>
          <n-button size="small" @click="searchQuery = ''">清除搜索</n-button>
        </template>
      </n-empty>

      <!-- Article list -->
      <div v-else>
        <div v-for="item in filteredArticles" :key="item.id"
             class="article-row"
             @click="openDetail(item)">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <n-tag size="tiny" :type="item.sentiment==='bullish'?'error':item.sentiment==='bearish'?'success':'default'">
              {{ item.sentiment || 'neutral' }}
            </n-tag>
            <n-tag size="tiny" :bordered="false" style="background:rgba(217,119,6,0.1);color:#d97706">
              {{ item.riskLevel || 'low' }}
            </n-tag>
            <n-tag size="tiny" :bordered="false">{{ item.region || 'cn' }}</n-tag>
            <span style="font-size:14px;flex:1;color:#333">{{ item.title?.substring(0, 100) }}</span>
            <!-- Delete button -->
            <n-popconfirm
              @positive-click="deleteArticle(item)"
              @click.stop
            >
              <template #trigger>
                <n-button
                  size="tiny"
                  quaternary
                  type="error"
                  @click.stop
                  :loading="deletingId === item.id"
                  :disabled="deletingId !== null"
                  style="flex-shrink:0;opacity:0.5"
                  title="删除此文章"
                >
                  <span style="font-size:14px">&times;</span>
                </n-button>
              </template>
              确定删除这篇文章吗？此操作不可撤销。
            </n-popconfirm>
          </div>
          <div style="font-size:12px;color:#999;display:flex;gap:12px">
            <span>{{ item.sourceName }}</span>
            <span>{{ item.publishedAt?.substring(0, 10) }}</span>
            <span v-if="item.summary" style="color:#666">{{ item.summary?.substring(0, 80) }}...</span>
          </div>
        </div>
      </div>

      <n-pagination v-if="total > pageSize" :page="page" :page-size="pageSize"
                    :item-count="total" @update:page="onPageChange"
                    style="margin-top:16px;justify-content:center" />
    </n-card>

    <!-- Detail Modal -->
    <n-modal v-model:show="showDetail" style="width:700px" v-if="selectedArticle">
      <n-card :title="selectedArticle.title" size="small" closable @close="showDetail = false">
        <div style="font-size:12px;color:#999;margin-bottom:12px">
          {{ selectedArticle.sourceName }} · {{ selectedArticle.publishedAt?.substring(0, 10) }} · {{ selectedArticle.region }}
          <a v-if="selectedArticle.url" :href="selectedArticle.url" target="_blank" rel="noopener noreferrer"
             style="margin-left:12px;color:#d97706;text-decoration:none">查看原文 &#8599;</a>
        </div>
        <div v-if="selectedArticle.analysis" style="margin-bottom:12px">
          <n-space>
            <n-tag type="warning" size="small">情感: {{ selectedArticle.analysis.sentiment }} ({{ selectedArticle.analysis.sentimentScore }})</n-tag>
            <n-tag type="info" size="small">风险: {{ selectedArticle.analysis.riskLevel }}</n-tag>
            <n-tag size="small">引擎: {{ selectedArticle.analysis.engine }}</n-tag>
          </n-space>
        </div>
        <div style="font-size:13px;line-height:1.7;color:#555;max-height:400px;overflow-y:auto;white-space:pre-wrap">
          {{ selectedArticle.content || '(文章正文未抓取，点击上方链接查看原文)' }}
        </div>
        <div v-if="selectedArticle.analysis?.entities" style="margin-top:12px;font-size:12px">
          <div v-for="(names, etype) in selectedArticle.analysis.entities" :key="etype" style="margin-top:4px">
            <strong>{{ etype }}:</strong>
            <n-tag v-for="name in (names as string[]).slice(0, 5)" :key="name" size="tiny" style="margin:2px">{{ name }}</n-tag>
          </div>
        </div>
      </n-card>
    </n-modal>
  </div>
</template>

<style scoped>
/* ── Article row ── */
.article-row {
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.12s;
}
.article-row:hover {
  background: #fafafa;
}
.article-row:last-child {
  border-bottom: none;
}

/* ── Delete button hover reveal ── */
.article-row .n-button {
  opacity: 0;
  transition: opacity 0.15s;
}
.article-row:hover .n-button {
  opacity: 0.55;
}
</style>
