<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import api from '@/api/client'
import { NCard, NButton, NSpace, NTag, NEmpty, NGrid, NGi, useMessage } from 'naive-ui'

const store = useAppStore()
const message = useMessage()
const reports = ref<any[]>([])
const selectedReport = ref<any>(null)
const loading = ref(false)
const generating = ref(false)
const generatingAI = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const { data } = await api.get('/reports', { params: { pageSize: 20 } })
    reports.value = data.list || []
    if (reports.value.length) {
      await loadReport(reports.value[0].id)
    }
  } catch {}
})

onUnmounted(() => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
})

async function loadReport(id: string) {
  loading.value = true
  try {
    const { data } = await api.get(`/reports/${id}`)
    selectedReport.value = data.report
  } catch {
    message.error('加载报告失败')
  }
  loading.value = false
}

async function generateReport() {
  generating.value = true
  try {
    const { data: pipeResp } = await api.post('/pipeline/analyze', null, {
      params: {
        date_from: store.dateFrom,
        date_to: store.dateTo,
      },
    })
    message.success('报告生成任务已启动，正在分析中...')

    let attempts = 0
    const maxAttempts = 60
    pollTimer = setInterval(async () => {
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(pollTimer!)
        pollTimer = null
        generating.value = false
        message.warning('报告生成超时，请稍后手动刷新')
        return
      }
      try {
        const { data: status } = await api.get('/pipeline/status')
        if (!status.pipeline?.active) {
          clearInterval(pollTimer!)
          pollTimer = null
          const { data: reportResp } = await api.get('/reports/latest')
          if (reportResp.found) {
            selectedReport.value = reportResp.report
            const exists = reports.value.some((r: any) => r.id === reportResp.report.id)
            if (!exists) {
              reports.value.unshift(reportResp.report)
            }
            message.success('报告生成完成！')
          } else {
            message.warning('分析完成但未生成报告，请检查数据量')
          }
          generating.value = false
        }
      } catch {
        // Ignore poll errors
      }
    }, 2000)
  } catch (e: any) {
    message.error('启动报告生成失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
    generating.value = false
  }
}

// ──────────────────────────────────────────────────
// formatReportText — markdown-style text formatting
// ──────────────────────────────────────────────────

// Known government/institution names (Chinese + English)
const INSTITUTION_PATTERNS = [
  '央行', '中国人民银行', '美联储', 'Federal Reserve', 'Fed',
  '国务院', '发改委', '财政部', '商务部', '工信部', '住建部', '外交部',
  '证监会', '银保监会', '银监会', '保监会', '外管局',
  'PBOC', 'ECB', '欧洲央行', '日本央行', 'BOJ', 'BOE', '英国央行',
  'OPEC', 'IMF', '国际货币基金组织', '世界银行', 'World Bank',
  '国务院常务会议', '中央经济工作会议', '全国人大',
  '统计局', '海关总署', '国家税务总局',
  'SEC', 'CFTC', 'FDIC',
]

// Build a single regex that matches any institution name (word-boundary aware)
function buildInstitutionRegex(): RegExp {
  const escaped = INSTITUTION_PATTERNS
    .sort((a, b) => b.length - a.length) // longest first to avoid partial matches
    .map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  return new RegExp(`(${escaped.join('|')})`, 'gi')
}

// Known company patterns (common A-share / global entities likely to appear in reports)
const COMPANY_PATTERNS = [
  '贵州茅台', '宁德时代', '比亚迪', '腾讯', '阿里巴巴', 'Alibaba', 'Tencent',
  '华为', 'Huawei', '小米', 'Xiaomi', '字节跳动', 'ByteDance', '特斯拉', 'Tesla',
  '苹果', 'Apple', '微软', 'Microsoft', '谷歌', 'Google', 'Alphabet',
  '英伟达', 'NVIDIA', 'AMD', 'Intel', '英特尔', '台积电', 'TSMC',
  '工商银行', '建设银行', '农业银行', '中国银行', '招商银行',
  '中国平安', '中国人寿', '中信证券', '华泰证券',
  '中石油', '中石化', '中海油', '中国神华',
  '万科', '碧桂园', '保利', '华润',
  '京东', 'JD', '美团', 'Meituan', '拼多多', 'PDD',
  '网易', 'NetEase', '百度', 'Baidu',
  '恒瑞医药', '药明康德', '迈瑞医疗',
  '隆基绿能', '阳光电源', '通威股份',
  '工商银行', '招商银行', '兴业银行',
]

function buildCompanyRegex(): RegExp {
  const escaped = COMPANY_PATTERNS
    .sort((a, b) => b.length - a.length)
    .map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  return new RegExp(`(${escaped.join('|')})`, 'gi')
}

/**
 * Format raw report text with styled spans:
 *  - Dates         → subtle highlight background
 *  - Numbers/%     → bold, red/green based on sign
 *  - Institutions  → amber tag
 *  - Companies     → blue tag
 *  - URLs          → clickable links
 */
function formatReportText(raw: string): string {
  if (!raw) return ''

  const institutionRe = buildInstitutionRegex()
  const companyRe = buildCompanyRegex()

  // Step 1: Escape HTML entities
  let html = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Step 2: URLs → clickable links (before other transforms to avoid nested spans)
  html = html.replace(
    /(https?:\/\/[^\s<>"'，。；！？、]+)/g,
    '<a href="$1" target="_blank" rel="noopener" class="fmt-link">$1</a>'
  )

  // Step 3: Dates with subtle highlight
  // YYYY-MM-DD, YYYY/MM/DD
  html = html.replace(
    /\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b/g,
    '<span class="fmt-date">$1</span>'
  )
  // Chinese dates: "2026年7月", "2026年7月26日"
  html = html.replace(
    /(\d{4}年\d{1,2}月\d{0,2}日?)/g,
    '<span class="fmt-date">$1</span>'
  )
  // Short date: "7月26日"
  html = html.replace(
    /(?<!\d)(\d{1,2}月\d{1,2}日)(?!\d)/g,
    '<span class="fmt-date">$1</span>'
  )

  // Step 4: Institution names → amber highlight (must run before company matching
  // since some institution names contain company-like substrings)
  html = html.replace(institutionRe, (match) => {
    return `<span class="fmt-institution">${match}</span>`
  })

  // Step 5: Company names → blue highlight
  html = html.replace(companyRe, (match) => {
    return `<span class="fmt-company">${match}</span>`
  })

  // Step 6: Numbers with % → colored (red=positive, green=negative, default=bold)
  // Matches patterns like: +3.5%, -1.2%, 3.5%, ↑2.1%, ↓0.8%
  html = html.replace(
    /([+↑]?\d+(?:[,.]?\d+)*\.?\d*\s*%|[-↓]\d+(?:[,.]?\d+)*\.?\d*\s*%)/g,
    (match) => {
      // Determine sign
      const isNeg = /^[-↓]/.test(match)
      const isPos = /^[+↑]/.test(match)
      let cls = 'fmt-number-neutral'
      if (isNeg) cls = 'fmt-number-down'
      else if (isPos) cls = 'fmt-number-up'
      else {
        // Bare number like "3.5%" — check if there's a preceding context
        // we treat bare percentages as neutral-bold
      }
      return `<span class="fmt-number ${cls}">${match}</span>`
    }
  )

  // Step 7: Large bare numbers (thousands, millions) → bold
  // e.g. "1,234.56", "$3,500", "US$1,200"
  html = html.replace(
    /((?:[¥$€£]|US\$|RMB)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?)/g,
    (match) => {
      // Skip if already inside a span or link
      return `<span class="fmt-number fmt-number-neutral">${match}</span>`
    }
  )

  // Step 8: VIX恐慌、避险 等关键词 → subtle emphasis
  html = html.replace(
    /(恐慌升温|恐慌|避险情绪升温|避险)/g,
    '<span class="fmt-risk">$1</span>'
  )

  return html
}

// Section title mapping
const SECTION_TITLES: Record<string, string> = {
  economy: '经济 Economy',
  politics: '政治 Politics',
  business: '商业 Business',
  technology: '科技 Technology',
  culture: '文化 Culture',
  society: '社会 Society',
  markets: '市场 Markets',
}

async function generateAIReport() {
  generatingAI.value = true
  try {
    const { data } = await api.post('/reports/generate-ai', null, {
      params: { date_from: store.dateFrom, date_to: store.dateTo },
    })
    if (data.ok) {
      selectedReport.value = data.report
      const exists = reports.value.some((r: any) => r.id === data.report.id)
      if (!exists) reports.value.unshift(data.report)
      message.success('AI报告生成完成！四位专家共同撰写。')
    } else {
      message.error(data.error || 'AI报告生成失败')
    }
  } catch (e: any) {
    message.error('AI报告生成失败: ' + (e.response?.data?.detail || e.message || '请检查AI模型配置'))
  }
  generatingAI.value = false
}
</script>

<template>
  <div>
    <n-space style="margin-bottom: 16px" justify="space-between">
      <h3 style="margin: 0; font-size: 18px; font-weight: 700">宏观日报</h3>
      <n-space>
        <n-button type="primary" size="small" @click="generateReport"
                  :loading="generating" :disabled="generating || generatingAI">
          {{ generating ? '生成中...' : '规则报告' }}
        </n-button>
        <n-button type="warning" size="small" @click="generateAIReport"
                  :loading="generatingAI" :disabled="generating || generatingAI">
          {{ generatingAI ? 'AI写作中...' : 'AI多Agent报告' }}
        </n-button>
      </n-space>
    </n-space>

    <n-grid :cols="[1, 3]" :x-gap="16">
      <!-- Report List -->
      <n-gi :span="1">
        <n-card title="报告列表" size="small">
          <div v-if="reports.length">
            <div v-for="r in reports" :key="r.id"
                 @click="loadReport(r.id)"
                 :style="{
                   padding: '10px 8px',
                   cursor: 'pointer',
                   borderRadius: '6px',
                   marginBottom: '4px',
                   background: selectedReport?.id === r.id ? '#fef3c7' : 'transparent',
                   border: selectedReport?.id === r.id ? '1px solid #fcd34d' : '1px solid transparent',
                   transition: 'all 0.15s',
                 }">
              <div style="font-size: 13px; font-weight: 600; line-height: 1.4">{{ r.headline?.substring(0, 42) }}{{ (r.headline?.length || 0) > 42 ? '...' : '' }}</div>
              <div style="font-size: 11px; color: #999; margin-top: 4px">
                {{ r.periodStart?.substring(0, 10) }}
                <span style="margin: 0 4px">·</span>
                {{ r.articleCount }}篇
                <span style="margin: 0 4px">·</span>
                <span :style="{ color: r.marketSentiment === 'bullish' ? '#dc2626' : r.marketSentiment === 'bearish' ? '#16a34a' : '#888', fontWeight: 600 }">
                  {{ r.marketSentiment }}
                </span>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无报告，请点击上方按钮生成" size="small" />
        </n-card>
      </n-gi>

      <!-- Report Content -->
      <n-gi :span="2">
        <n-card v-if="selectedReport" size="small">
          <!-- Header -->
          <div style="margin-bottom: 18px">
            <h2 style="margin: 0 0 8px 0; font-size: 20px; font-weight: 700; line-height: 1.4">
              {{ selectedReport.headline }}
            </h2>
            <n-space align="center">
              <n-tag
                :type="selectedReport.marketSentiment === 'bullish' ? 'error' : selectedReport.marketSentiment === 'bearish' ? 'success' : 'default'"
                size="small"
                :bordered="false"
              >
                {{ selectedReport.marketSentiment }}
              </n-tag>
              <span style="font-size: 12px; color: #999">
                {{ selectedReport.periodStart?.substring(0, 10) }} ~ {{ selectedReport.periodEnd?.substring(0, 10) }}
                <span style="margin: 0 6px">·</span>
                {{ selectedReport.articleCount }} 篇文章
              </span>
            </n-space>
          </div>

          <!-- Executive Summary -->
          <div class="exec-summary">
            <div class="exec-summary-label">执行摘要</div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="exec-summary-text" v-html="formatReportText(selectedReport.executiveSummary || '')" />
          </div>

          <!-- Sections -->
          <div v-if="selectedReport.sections" class="report-sections">
            <div v-for="(content, key) in selectedReport.sections" :key="key" class="report-section">
              <h4 class="section-title">
                {{ SECTION_TITLES[String(key)] || key }}
              </h4>
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div class="section-content" v-html="formatReportText(String(content || '(暂无内容)'))" />
            </div>
          </div>
        </n-card>
        <n-empty v-else description="选择一份报告查看" size="small" style="margin-top: 40px" />
      </n-gi>
    </n-grid>
  </div>
</template>

<style scoped>
/* ── Executive Summary ── */
.exec-summary {
  background: #fafaf7;
  padding: 16px 18px;
  border-radius: 8px;
  margin-bottom: 18px;
  border: 1px solid #f0efe8;
}
.exec-summary-label {
  font-size: 11px;
  font-weight: 700;
  color: #d97706;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-bottom: 8px;
}
.exec-summary-text {
  font-size: 14px;
  line-height: 1.85;
  color: #444;
}

/* ── Sections ── */
.report-sections {
  margin-top: 8px;
}
.report-section {
  margin-bottom: 22px;
}
.section-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 700;
  color: #d97706;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0ebe0;
  letter-spacing: 0.3px;
}
.section-content {
  font-size: 13px;
  line-height: 1.8;
  color: #555;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Formatted text spans ── */
:deep(.fmt-date) {
  background: #fef9e7;
  color: #92400e;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.92em;
  font-weight: 500;
  white-space: nowrap;
}

:deep(.fmt-institution) {
  background: #fef3c7;
  color: #92400e;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  font-size: 0.93em;
  white-space: nowrap;
}

:deep(.fmt-company) {
  background: #dbeafe;
  color: #1e40af;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  font-size: 0.93em;
  white-space: nowrap;
}

:deep(.fmt-number) {
  font-weight: 700;
  font-size: 0.96em;
}
:deep(.fmt-number-up) {
  color: #dc2626;
}
:deep(.fmt-number-down) {
  color: #16a34a;
}
:deep(.fmt-number-neutral) {
  color: #1f2937;
}

:deep(.fmt-link) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
  word-break: break-all;
}
:deep(.fmt-link:hover) {
  color: #7c3aed;
}

:deep(.fmt-risk) {
  color: #dc2626;
  font-weight: 600;
}
</style>
