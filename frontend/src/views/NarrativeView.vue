<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { NCard, NButton, NModal, NInput, NTag, NSpace, NGrid, NGi, NEmpty, useMessage } from 'naive-ui'

const message = useMessage()
const themes = ref<any[]>([])
const divergence = ref<any[]>([])
const showCreate = ref(false)
const newTheme = ref({ name: '', description: '', keywords: '' })
const creating = ref(false)

onMounted(async () => {
  try {
    const [t, d] = await Promise.all([
      api.get('/narrative/themes'),
      api.get('/narrative/divergence'),
    ])
    themes.value = t.data.list || []
    divergence.value = d.data.list || []
  } catch {}
})

async function createTheme() {
  if (!newTheme.value.name.trim()) {
    message.warning('请输入主题名称')
    return
  }
  creating.value = true
  const kw = newTheme.value.keywords.split(',').map(k => k.trim()).filter(Boolean)
  try {
    await api.post('/narrative/themes', { name: newTheme.value.name, description: newTheme.value.description, keywords: kw })
    message.success('叙事主题创建成功')
    showCreate.value = false
    newTheme.value = { name: '', description: '', keywords: '' }
    const { data } = await api.get('/narrative/themes')
    themes.value = data.list || []
  } catch (e: any) {
    message.error('创建失败: ' + (e.response?.data?.detail || e.message || '未知错误'))
  }
  creating.value = false
}

// Simple SVG for divergence
const maxDiv = ref(1)
</script>

<template>
  <div>
    <n-space style="margin-bottom:16px" justify="space-between">
      <h3 style="margin:0">叙事分析</h3>
      <n-button size="small" @click="showCreate = true">+ 新建追踪主题</n-button>
    </n-space>

    <!-- Divergence visualization -->
    <n-card title="跨区域情绪分歧" size="small" style="margin-bottom:16px">
      <div v-if="divergence.length" style="overflow-x:auto">
        <svg :viewBox="`0 0 ${divergence.length * 100 + 100} 220`" style="width:100%;height:250px">
          <line x1="80" y1="10" x2="80" y2="190" stroke="#ddd" stroke-width="1" />
          <line x1="80" y1="190" :x2="divergence.length * 100 + 20" y2="190" stroke="#ddd" stroke-width="1" />
          <line x1="80" y1="100" :x2="divergence.length * 100 + 20" y2="100" stroke="#eee" stroke-width="1" stroke-dasharray="4" />
          <text x="70" y="14" text-anchor="end" font-size="10" fill="#999">1.0</text>
          <text x="70" y="104" text-anchor="end" font-size="10" fill="#999">0.0</text>
          <g v-for="(d, i) in divergence" :key="d.themeId">
            <rect :x="90 + i * 100" :y="190 - d.divergence * 90" width="16" height="0" fill="#d97706" rx="2">
              <animate attributeName="height" :to="d.divergence * 90" dur="0.5s" fill="freeze" />
              <animate attributeName="y" :to="190 - d.divergence * 90" dur="0.5s" fill="freeze" />
            </rect>
            <text :x="98 + i * 100" y="208" text-anchor="middle" font-size="9" fill="#666">
              {{ d.themeName?.substring(0, 8) }}
            </text>
          </g>
        </svg>
      </div>
      <n-empty v-else description="暂无叙事分歧数据" size="small" />
    </n-card>

    <n-grid :cols="3" :x-gap="12" :y-gap="12">
      <n-gi v-for="theme in themes" :key="theme.id">
        <n-card size="small" :title="theme.name">
          <div style="font-size:12px;color:#666;margin-bottom:8px">{{ theme.description }}</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            <n-tag v-for="kw in theme.keywords?.slice(0, 6)" :key="kw" size="tiny" :bordered="false"
                   style="background:rgba(217,119,6,0.1);color:#d97706">{{ kw }}</n-tag>
          </div>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-if="!themes.length" description="暂无追踪主题" size="small" style="margin-top:24px" />

    <n-modal v-model:show="showCreate" style="width:500px">
      <n-card title="新建叙事主题" size="small" closable @close="showCreate = false">
        <n-input v-model:value="newTheme.name" placeholder="主题名称" style="margin-bottom:8px" />
        <n-input v-model:value="newTheme.description" placeholder="描述" style="margin-bottom:8px" type="textarea" :rows="2" />
        <n-input v-model:value="newTheme.keywords" placeholder="关键词（逗号分隔）" style="margin-bottom:8px" />
        <n-button type="primary" size="small" @click="createTheme" :loading="creating" :disabled="creating">
          {{ creating ? '创建中...' : '创建' }}
        </n-button>
      </n-card>
    </n-modal>
  </div>
</template>
