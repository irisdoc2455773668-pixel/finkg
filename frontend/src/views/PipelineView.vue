<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import api from '@/api/client'
import { NCard, NButton, NSpace, NTag, NProgress, NEmpty, NGrid, NGi, useMessage } from 'naive-ui'

const store = useAppStore()
const message = useMessage()
const crawlStatus = ref<any>(null)
const pipelineState = ref<any>(null)
const tasks = ref<any[]>([])

// Individual loading states per operation
const runningFull = ref(false)
const runningCrawl = ref(false)
const runningAnalyze = ref(false)
const refreshingMarket = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => { refresh() })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

async function refresh() {
  try {
    const { data } = await api.get('/pipeline/status')
    crawlStatus.value = data.crawl
    pipelineState.value = data.pipeline
  } catch {}
  try {
    const { data } = await api.get('/pipeline/tasks', { params: { pageSize: 10 } })
    tasks.value = data.list || []
  } catch {}
}

async function triggerCrawl() {
  runningCrawl.value = true
  try {
    await api.post('/pipeline/crawl/news', null, {
      params: { date_from: store.dateFrom, date_to: store.dateTo },
    })
    message.success('新闻抓取已启动')
    startPolling()
  } catch (e: any) {
    message.error('抓取失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    runningCrawl.value = false
  }
}

async function triggerMarket() {
  refreshingMarket.value = true
  try {
    const { data } = await api.post('/pipeline/crawl/market')
    if (data.ok) {
      message.success(`已刷新 ${data.count} 个市场指标`)
    } else {
      message.error(data.error || '刷新失败')
    }
  } catch (e: any) {
    message.error('刷新失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  }
  refreshingMarket.value = false
}

async function triggerAnalyze() {
  runningAnalyze.value = true
  try {
    await api.post('/pipeline/analyze', null, {
      params: { date_from: store.dateFrom, date_to: store.dateTo },
    })
    message.success('分析管道已启动')
    startPolling()
  } catch (e: any) {
    message.error('分析失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    runningAnalyze.value = false
  }
}

async function triggerFull() {
  runningFull.value = true
  try {
    await api.post('/pipeline/full', null, {
      params: { date_from: store.dateFrom, date_to: store.dateTo },
    })
    message.success('全流程已启动（抓取 -> 分析 -> 报告）')
    startPolling()
  } catch (e: any) {
    message.error('启动失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    runningFull.value = false
  }
}

function isAnyRunning(): boolean {
  return runningFull.value || runningCrawl.value || runningAnalyze.value
}

function clearAllRunning() {
  runningFull.value = false
  runningCrawl.value = false
  runningAnalyze.value = false
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    await refresh()
    if (!crawlStatus.value?.active && !pipelineState.value?.active) {
      clearInterval(pollTimer!)
      pollTimer = null
      clearAllRunning()
      message.success('任务完成！')
      await store.fetchStatus()
    }
  }, 2000)
}

function stageStatus(status: string) {
  if (status === 'done') return 'success'
  if (status === 'running') return 'warning'
  return 'default'
}
</script>

<template>
  <div>
    <!-- Date range info -->
    <div style="font-size:12px;color:#999;margin-bottom:16px;background:#fafaf7;padding:8px 12px;border-radius:6px">
      当前时间范围: <strong>{{ store.dateFrom }}</strong> ~ <strong>{{ store.dateTo }}</strong>
      <span style="margin-left:16px">（在顶部导航栏调整时间范围，所有操作将基于此范围执行）</span>
    </div>

    <n-space style="margin-bottom:24px">
      <n-button type="primary" size="large" @click="triggerFull"
                :loading="runningFull" :disabled="isAnyRunning()">
        {{ runningFull ? '全流程运行中...' : '全流程运行' }}
      </n-button>
      <n-button @click="triggerCrawl"
                :loading="runningCrawl" :disabled="isAnyRunning()">
        {{ runningCrawl ? '抓取中...' : '抓取新闻' }}
      </n-button>
      <n-button @click="triggerAnalyze"
                :loading="runningAnalyze" :disabled="isAnyRunning()">
        {{ runningAnalyze ? '分析中...' : '分析管道' }}
      </n-button>
      <n-button @click="triggerMarket" :loading="refreshingMarket" :disabled="refreshingMarket">
        {{ refreshingMarket ? '刷新中...' : '刷新行情' }}
      </n-button>
    </n-space>

    <n-grid :cols="2" :x-gap="16">
      <!-- Crawl Progress -->
      <n-gi>
        <n-card title="抓取进度" size="small">
          <div v-if="crawlStatus">
            <n-progress type="line"
                        :percentage="crawlStatus.total_sources > 0 ? Math.round(crawlStatus.completed_sources / crawlStatus.total_sources * 100) : 0"
                        :height="20" :border-radius="4" :fill-border-radius="0"
                        :status="crawlStatus.active ? 'warning' : 'success'" />
            <div style="font-size:12px;color:#999;margin-top:8px">
              <template v-if="crawlStatus.active">
                {{ crawlStatus.completed_sources }}/{{ crawlStatus.total_sources }} 源完成 ·
                已找到 {{ crawlStatus.articlesFound }} 篇
                <span v-if="crawlStatus.currentSource">· 当前: {{ crawlStatus.currentSource }}</span>
              </template>
              <template v-else>
                空闲 · 共 {{ crawlStatus.total_sources }} 个源可用
              </template>
            </div>
          </div>
          <n-empty v-else description="正在加载..." size="small" />
        </n-card>
      </n-gi>

      <!-- Pipeline Progress -->
      <n-gi>
        <n-card title="分析管道" size="small">
          <div v-if="pipelineState?.stages">
            <n-progress type="line" :percentage="pipelineState.progress || 0" :height="20"
                        :status="pipelineState.active ? 'warning' : 'success'" />
            <div style="margin-top:12px">
              <div v-for="(stage, i) in pipelineState.stages" :key="i"
                   style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:12px">
                <n-tag size="tiny" :type="stageStatus(stage.status)" :bordered="false">
                  {{ stage.status === 'done' ? 'OK' : stage.status === 'running' ? '...' : '--' }}
                </n-tag>
                <span :style="{color: stage.status === 'pending' ? '#ccc' : '#333'}">{{ stage.name }}</span>
              </div>
            </div>
          </div>
          <n-empty v-else description="无运行中的分析任务" size="small" />
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Task History -->
    <n-card title="任务历史" size="small" style="margin-top:16px">
      <div v-if="tasks.length">
        <div v-for="t in tasks" :key="t.id"
             style="display:flex;justify-content:space-between;padding:6px 10px;font-size:12px;border-bottom:1px solid #f5f5f5;align-items:center">
          <span>
            <n-tag size="tiny" :type="t.status==='done'?'success':t.status==='failed'?'error':'warning'">
              {{ t.status }}
            </n-tag>
            <span style="margin-left:8px">{{ t.taskType }}</span>
            <span v-if="t.totalItems" style="margin-left:8px;color:#999">{{ t.totalItems }} 项</span>
          </span>
          <span style="color:#999;font-size:11px">{{ t.startedAt?.substring(0, 19) }}</span>
        </div>
      </div>
      <n-empty v-else description="暂无任务记录" size="small" />
    </n-card>
  </div>
</template>
