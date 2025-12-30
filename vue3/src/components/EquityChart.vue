<template>
  <div class="chart-card">
    <div class="header">
      <h3>策略回测资金曲线</h3>
      <button @click="fetchData" class="refresh-btn">刷新数据</button>
    </div>
    <div ref="chartRef" class="echarts-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';

const chartRef = ref(null);
let myChart = null;

// 获取并渲染数据
const fetchData = async () => {
  try {
    const res = await axios.get('http://localhost:5000/api/backtest/equity');
    if (res.data.code === 200) {
      renderChart(res.data.data);
    }
  } catch (error) {
    console.error("无法加载资金曲线数据:", error);
  }
};

const renderChart = (rawData) => {
  if (!myChart) myChart = echarts.init(chartRef.value);
  const dates = rawData.map(item => item.date);
  const values = rawData.map(item => item.value);
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const data = params[0];
        return `日期: ${data.name}<br/>总资产: <span style="color:#ef5350">¥${data.value.toLocaleString()}</span>`;
      }
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#999' } }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: { formatter: '¥{value}' },
      splitLine: { lineStyle: { type: 'dashed' } }
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100 }],
    series: [{
      name: '总资产',
      type: 'line',
      data: values,
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 3, color: '#2196f3' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(33, 150, 243, 0.3)' },
          { offset: 1, color: 'rgba(33, 150, 243, 0)' }
        ])
      }
    }]
  };
  myChart.setOption(option);
};

const handleResize = () => myChart && myChart.resize();

onMounted(() => {
  fetchData();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (myChart) myChart.dispose();
});
</script>

<style scoped>
.chart-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  padding: 20px;
  margin: 20px 0;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.echarts-container {
  width: 100%;
  height: 500px;
}
.refresh-btn {
  padding: 6px 16px;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.refresh-btn:hover { background: #1976d2; }
</style>
