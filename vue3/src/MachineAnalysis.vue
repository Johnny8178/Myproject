<template>
  <div class="pc-layout">
    <aside class="pc-sidebar">
      <div class="brand">机器分析系统</div>
      <div class="control-group">
        <label>股票代码</label>
        <input v-model="symbol" class="dark-input" placeholder="如 600316" />
        <button class="action-btn" @click="handleAnalyze" :disabled="loading">
          {{ loading ? '计算中...' : '执行深度分析' }}
        </button>
      </div>
      <div class="system-info">
        系统状态: 运行中<br />
        计算内核: FFT + 价格还原
      </div>
    </aside>
    <main class="pc-main">
      <section class="pc-card">
        <div class="card-title">主力波深度观察 (真实价格空间)</div>
        <div class="img-container">
          <img v-if="imageUrl" :src="imageUrl" class="fit-img" />
          <div v-else class="empty-state">等待数据生成...</div>
        </div>
      </section>
      <section class="pc-card">
        <div class="card-title">策略回测绩效 (JSON 动态渲染)</div>
        <div class="img-container">
          <EquityChart />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const symbol = ref('600316')
const loading = ref(false)
const imageUrl = ref('')

const handleAnalyze = async () => {
  loading.value = true
  imageUrl.value = ''
  try {
    // 调用后端分析接口，带 symbol 参数
    const res = await axios.get('http://localhost:5000/analyze', { params: { symbol: symbol.value } })
    if (res.data && res.data.img_url) {
      imageUrl.value = 'http://localhost:5000' + res.data.img_url
    } else {
      imageUrl.value = ''
      alert('未获取到分析图片')
    }
  } catch (e) {
    imageUrl.value = ''
    alert('分析失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 强制让容器占满整个浏览器视口，并靠左对齐 */
.pc-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background-color: #f5f7fa;
  justify-content: flex-start; /* 靠左对齐 */
  align-items: flex-start;     /* 顶部对齐 */
}

/* 左侧侧边栏：固定宽度 260px，不再随屏幕伸缩 */
.pc-sidebar {
  width: 260px; 
  min-width: 260px;
  background: #1e222d;
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 40px 20px;
  box-sizing: border-box;
  z-index: 100;
}

/* 右侧主内容区：自动撑开占满剩余所有空间 */
.pc-main {
  flex: 1; 
  height: 100vh;
  overflow-y: auto; /* 只有这里可以上下滚动 */
  padding: 40px;
  box-sizing: border-box;
}

/* 品牌标题样式 */
.brand {
  font-size: 22px;
  font-weight: 800;
  color: #409eff;
  margin-bottom: 60px;
  text-align: center;
  letter-spacing: 1px;
}

/* 输入框和按钮组 */
.control-group {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.dark-input {
  width: 100%;
  padding: 12px;
  background: #2b3139;
  border: 1px solid #474d57;
  color: #fff;
  border-radius: 4px;
  box-sizing: border-box;
}

.action-btn {
  width: 100%;
  padding: 15px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn:hover {
  background: #66b1ff;
  transform: translateY(-2px);
}

/* 右侧卡片布局：利用栅格或并排显示 */
.pc-card {
  background: #fff;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  width: 100%; /* 卡片宽度跟随主内容区 */
  box-sizing: border-box;
}

.card-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 25px;
  color: #1e2329;
  border-left: 5px solid #409eff;
  padding-left: 15px;
}

.img-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #fafafa;
  border-radius: 8px;
  padding: 20px;
  box-sizing: border-box;
}

.fit-img {
  max-width: 100%; /* 图片宽度自适应卡片 */
  height: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

/* 系统状态信息置于侧边栏底部 */
.system-info {
  margin-top: auto; /* 推到最底部 */
  padding-top: 20px;
  border-top: 1px solid #333;
  font-size: 12px;
  color: #848e9c;
  line-height: 2;
}
</style>
