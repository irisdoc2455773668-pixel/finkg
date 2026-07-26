<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { NCard, NTabs, NTabPane, NInput, NButton, NSelect, NSlider, NSwitch, NSpace, NTag, NEmpty, NPopconfirm, useMessage, NModal, NForm, NFormItem } from 'naive-ui'

const message = useMessage()

// ── AI Config ──
const aiConfig = ref({
  provider: 'openai', base_url: 'https://api.deepseek.com/v1', api_key: '',
  model_name: 'deepseek-chat', temperature: 0.7, max_tokens: 4096,
  daily_token_limit: 100000
})
const aiConfigured = ref(false)
const tokensToday = ref(0)
const testing = ref(false)
const saving = ref(false)

const providerOptions = [
  { label: 'OpenAI 兼容 (DeepSeek/通义千问/Moonshot/智谱等)', value: 'openai' },
  { label: 'Anthropic Claude', value: 'anthropic' },
]

const modelPresets: Record<string, { url: string; model: string }> = {
  deepseek: { url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  qwen: { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  moonshot: { url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k' },
  zhipu: { url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash' },
  openai: { url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  custom: { url: '', model: '' },
}
const selectedPreset = ref('deepseek')

function applyPreset(key: string) {
  const p = modelPresets[key]
  if (p && key !== 'custom') {
    aiConfig.value.base_url = p.url
    aiConfig.value.model_name = p.model
  }
}

async function loadAIConfig() {
  try {
    const { data } = await api.get('/settings/ai')
    aiConfigured.value = data.configured
    tokensToday.value = data.tokens_used_today || 0
    if (data.configured) {
      aiConfig.value.provider = data.provider
      aiConfig.value.base_url = data.base_url
      aiConfig.value.model_name = data.model_name
      aiConfig.value.temperature = data.temperature
      aiConfig.value.max_tokens = data.max_tokens
      aiConfig.value.daily_token_limit = data.daily_token_limit
      aiConfig.value.api_key = data.api_key // masked
    }
  } catch {}
}

async function saveAIConfig() {
  saving.value = true
  try {
    await api.put('/settings/ai', aiConfig.value)
    message.success('AI配置已保存')
    await loadAIConfig()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || ''))
  }
  saving.value = false
}

async function testConnection() {
  testing.value = true
  try {
    const { data } = await api.post('/settings/ai/test')
    if (data.ok) message.success(data.message)
    else message.error(data.message)
  } catch (e: any) {
    message.error('测试失败')
  }
  testing.value = false
}

// ── Sources ──
const sources = ref<any[]>([])
const showSourceModal = ref(false)
const editingSource = ref<any>(null)
const sourceForm = ref({ name: '', url: '', source_type: 'rss', language: 'zh', region: 'cn', category: 'economy', is_active: true })

async function loadSources() {
  try {
    const { data } = await api.get('/settings/sources')
    sources.value = data.list || []
  } catch {}
}

function openAddSource() {
  editingSource.value = null
  sourceForm.value = { name: '', url: '', source_type: 'rss', language: 'zh', region: 'cn', category: 'economy', is_active: true }
  showSourceModal.value = true
}

function openEditSource(s: any) {
  editingSource.value = s
  sourceForm.value = { ...s }
  showSourceModal.value = true
}

async function saveSource() {
  try {
    if (editingSource.value) {
      await api.put(`/settings/sources/${editingSource.value.id}`, sourceForm.value)
    } else {
      await api.post('/settings/sources', sourceForm.value)
    }
    message.success('保存成功')
    showSourceModal.value = false
    await loadSources()
  } catch (e: any) {
    message.error('保存失败')
  }
}

async function deleteSource(id: string) {
  try {
    await api.delete(`/settings/sources/${id}`)
    message.success('已删除')
    await loadSources()
  } catch {}
}

async function toggleSource(id: string) {
  try {
    await api.post(`/settings/sources/${id}/toggle`)
    await loadSources()
  } catch {}
}

const regionLabels: Record<string, string> = { cn: '中国', us: '美国', eu: '欧洲', hk: '香港', jp: '日本', sg: '新加坡' }

onMounted(() => { loadAIConfig(); loadSources() })
</script>

<template>
  <div>
    <n-tabs type="line" animated>
      <!-- Tab 1: AI Config -->
      <n-tab-pane name="ai" tab="AI模型配置">
        <n-card title="LLM API 设置" size="small" style="max-width:700px">
          <n-space vertical :size="16">
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">模型供应商</div>
              <n-select v-model:value="aiConfig.provider" :options="providerOptions" style="width:100%" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">快速预设</div>
              <n-space>
                <n-button v-for="(_, key) in modelPresets" :key="key" size="tiny"
                          :type="selectedPreset === key ? 'primary' : 'default'"
                          @click="selectedPreset = key; applyPreset(key)">
                  {{ { deepseek: 'DeepSeek', qwen: '通义千问', moonshot: 'Moonshot', zhipu: '智谱', openai: 'OpenAI', custom: '自定义' }[key] }}
                </n-button>
              </n-space>
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">Base URL</div>
              <n-input v-model:value="aiConfig.base_url" placeholder="https://api.deepseek.com/v1" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">API Key</div>
              <n-input v-model:value="aiConfig.api_key" type="password" placeholder="sk-..." show-password-on="click" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">Model Name</div>
              <n-input v-model:value="aiConfig.model_name" placeholder="deepseek-chat" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">Temperature: {{ aiConfig.temperature }}</div>
              <n-slider v-model:value="aiConfig.temperature" :min="0" :max="2" :step="0.1" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">Max Tokens</div>
              <n-input-number v-model:value="aiConfig.max_tokens" :min="512" :max="32768" :step="512" style="width:200px" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">每日Token限额</div>
              <n-input-number v-model:value="aiConfig.daily_token_limit" :min="1000" :max="10000000" :step="10000" style="width:200px" />
              <span style="font-size:11px;color:#999;margin-left:8px">今日已用: {{ tokensToday.toLocaleString() }}</span>
            </div>
            <n-space>
              <n-button type="primary" @click="saveAIConfig" :loading="saving">保存配置</n-button>
              <n-button @click="testConnection" :loading="testing">测试连接</n-button>
            </n-space>
            <div v-if="aiConfigured" style="font-size:12px;color:#059669">AI已配置 · 今日已用 {{ tokensToday.toLocaleString() }} tokens</div>
            <div v-else style="font-size:12px;color:#999">尚未配置AI模型，AI报告生成功能不可用</div>
          </n-space>
        </n-card>
      </n-tab-pane>

      <!-- Tab 2: Sources -->
      <n-tab-pane name="sources" tab="数据源管理">
        <n-card size="small">
          <n-space style="margin-bottom:16px" justify="space-between">
            <span>共 {{ sources.length }} 个数据源</span>
            <n-button type="primary" size="small" @click="openAddSource">+ 添加数据源</n-button>
          </n-space>
          <div v-if="sources.length">
            <div v-for="s in sources" :key="s.id"
                 style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid #f0f0f0;font-size:13px">
              <div style="flex:1">
                <div style="display:flex;align-items:center;gap:8px">
                  <n-switch :value="s.isActive" @update:value="toggleSource(s.id)" size="small" />
                  <strong>{{ s.name }}</strong>
                  <n-tag size="tiny" :bordered="false">{{ s.sourceType }}</n-tag>
                  <n-tag size="tiny" :bordered="false" style="background:rgba(217,119,6,0.1);color:#d97706">{{ regionLabels[s.region] || s.region }}</n-tag>
                  <n-tag size="tiny" :bordered="false">{{ s.language }}</n-tag>
                </div>
                <div style="font-size:11px;color:#999;margin-top:2px;margin-left:44px">{{ s.url?.substring(0, 80) }}</div>
              </div>
              <n-space>
                <n-button text size="tiny" @click="openEditSource(s)">编辑</n-button>
                <n-popconfirm @positive-click="deleteSource(s.id)">
                  <template #trigger><n-button text size="tiny" style="color:#dc2626">删除</n-button></template>
                  确定删除此数据源？
                </n-popconfirm>
              </n-space>
            </div>
          </div>
          <n-empty v-else description="暂无数据源" size="small" />
        </n-card>
      </n-tab-pane>

      <!-- Tab 3: System -->
      <n-tab-pane name="system" tab="系统设置">
        <n-card title="系统参数" size="small" style="max-width:500px">
          <n-space vertical :size="16">
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">市场数据刷新间隔（分钟）</div>
              <n-input-number :value="5" :min="1" :max="1440" style="width:200px" />
            </div>
            <div>
              <div style="font-size:12px;color:#999;margin-bottom:4px">SOCKS5 代理</div>
              <n-input placeholder="127.0.0.1:9674" style="width:300px" />
            </div>
            <div style="font-size:12px;color:#999">
              当前数据库: SQLite (finkg.db) · 后端版本: v5.1 · API: http://localhost:8765
            </div>
          </n-space>
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- Add/Edit Source Modal -->
    <n-modal v-model:show="showSourceModal" style="width:500px">
      <n-card :title="editingSource ? '编辑数据源' : '添加数据源'" size="small" closable @close="showSourceModal = false">
        <n-space vertical :size="12">
          <n-input v-model:value="sourceForm.name" placeholder="名称（如：Reuters）" />
          <n-input v-model:value="sourceForm.url" placeholder="URL" />
          <n-select v-model:value="sourceForm.source_type" :options="[{label:'RSS',value:'rss'},{label:'Web',value:'web'}]" placeholder="类型" />
          <n-select v-model:value="sourceForm.region" :options="Object.entries(regionLabels).map(([k,v])=>({label:v,value:k}))" placeholder="地区" />
          <n-select v-model:value="sourceForm.language" :options="[{label:'中文',value:'zh'},{label:'英文',value:'en'}]" placeholder="语言" />
          <n-input v-model:value="sourceForm.category" placeholder="分类（economy/politics/business/technology）" />
          <n-button type="primary" @click="saveSource">保存</n-button>
        </n-space>
      </n-card>
    </n-modal>
  </div>
</template>
