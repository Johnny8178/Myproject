<template>
  <div class="container">
    <nav class="navbar">
      <div class="nav-placeholder">导航栏预留位置</div>
    </nav>

    <header class="main-title">
      <h1>机器分析</h1>
    </header>

    <section class="action-bar">
      <button @click="handleAnalysis" :disabled="isAnalyzing">
        {{ isAnalyzing ? '分析中...' : '分析' }}
      </button>
    </section>

    <footer class="display-area">
      <div v-if="showTable" class="result-container">
        <h3>分析结果</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>数值</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in tableData" :key="index">
              <td>{{ item.name }}</td>
              <td>{{ item.value }}</td>
              <td><span class="status-tag">正常</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">
        <p>暂无数据，请点击上方“分析”按钮</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

// 状态控制
const isAnalyzing = ref(false)
const showTable = ref(false)

// 模拟表格数据
const tableData = reactive([
  { name: 'CPU 使用率', value: '45%' },
  { name: '内存占用', value: '2.4 GB' },
  { name: '磁盘读取', value: '120 MB/s' },
  { name: '网络延迟', value: '15 ms' }
])

// 模拟分析按钮点击事件
const handleAnalysis = () => {
  isAnalyzing.value = true
  
  // 模拟一个 1 秒钟的分析过程
  setTimeout(() => {
    isAnalyzing.value = false
    showTable.value = true
  }, 1000)
}
</script>

<style scoped>
/* 基础布局 */
.container {
  font-family: Arial, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  color: #333;
}

/* 导航栏样式 */
.navbar {
  height: 60px;
  background-color: #2c3e50;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 20px;
  margin-bottom: 20px;
}

/* 标题样式 */
.main-title {
  text-align: center;
  margin: 30px 0;
}

/* 操作栏样式 */
.action-bar {
  display: flex;
  justify-content: center;
  gap: 15px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 30px;
}

button {
  padding: 10px 25px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

button:disabled {
  background-color: #95a5a6;
  cursor: not-allowed;
}

/* 表格样式 */
.display-area {
  min-height: 200px;
  border: 1px dashed #ccc;
  padding: 20px;
  border-radius: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

.data-table th, .data-table td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

.data-table th {
  background-color: #f2f2f2;
}

.status-tag {
  background-color: #e6f7ff;
  color: #1890ff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.empty-state {
  text-align: center;
  color: #999;
  margin-top: 50px;
}
</style>
