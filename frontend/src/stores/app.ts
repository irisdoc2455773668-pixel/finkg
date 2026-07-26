import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import api from '@/api/client'

export const useAppStore = defineStore('app', () => {
  const dateFrom = ref(dayjs().subtract(7, 'day').format('YYYY-MM-DD'))
  const dateTo = ref(dayjs().format('YYYY-MM-DD'))
  const status = ref<any>(null)
  const loading = ref(false)

  const dateRange = computed(() => ({
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
  }))

  async function fetchStatus() {
    loading.value = true
    try {
      const { data } = await api.get('/status')
      status.value = data
    } catch (e) {
      console.error('Failed to fetch status')
    } finally {
      loading.value = false
    }
  }

  return { dateFrom, dateTo, dateRange, status, loading, fetchStatus }
})
