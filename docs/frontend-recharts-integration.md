# 前端 Recharts 图表集成指南

本文档说明如何在 `agent-chat-ui` 前端项目中集成 Recharts 图表库，以替换后端 generative UI 中的简单 SVG 图表，获得更美观和交互性更强的图表效果。

## 1. 安装依赖

在 `agent-chat-ui` 项目中安装 Recharts：

```bash
npm install recharts
# 或
yarn add recharts
# 或
pnpm add recharts
```

## 2. 理解数据结构

后端 `SiteReportCard` 组件会传递以下图表数据结构：

### ChartData 类型定义

```typescript
interface ChartData {
  chart_type: "line" | "pie" | "bar";
  title: string;
  data: Array<Record<string, any>>;
  
  // 折线图专用
  x_key?: string;        // X轴数据字段名，如 "date"
  y_keys?: string[];     // Y轴数据字段名数组，如 ["visits", "unique_visitors"]
  y_key?: string;        // 单Y轴字段名（当只有一条线时）
  y_labels?: string[];   // Y轴显示标签，如 ["访问次数", "独立访客"]
  colors?: string[];     // 线条颜色数组
  
  // 饼图专用
  value_key?: string;    // 数值字段名，如 "value"
  label_key?: string;    // 标签字段名，如 "name"
  
  // 柱状图专用
  color?: string;        // 柱状图颜色
  show_change?: boolean; // 是否显示变化百分比
}
```

### 示例数据

**折线图数据：**
```json
{
  "chart_type": "line",
  "title": "每日访问趋势",
  "data": [
    { "date": "12/17", "visits": 1234, "unique_visitors": 890 },
    { "date": "12/18", "visits": 1456, "unique_visitors": 1023 },
    // ...
  ],
  "x_key": "date",
  "y_keys": ["visits", "unique_visitors"],
  "y_labels": ["访问次数", "独立访客"],
  "colors": ["#3b82f6", "#10b981"]
}
```

**饼图数据：**
```json
{
  "chart_type": "pie",
  "title": "流量来源分布",
  "data": [
    { "name": "直接访问", "value": 4500, "icon": "🔗", "color": "#3b82f6" },
    { "name": "搜索引擎", "value": 3200, "icon": "🔍", "color": "#10b981" },
    // ...
  ],
  "value_key": "value",
  "label_key": "name"
}
```

**柱状图数据：**
```json
{
  "chart_type": "bar",
  "title": "热门页面",
  "data": [
    { "name": "首页", "value": 8500, "change": 12.5 },
    { "name": "产品介绍", "value": 5200, "change": -3.2 },
    // ...
  ],
  "x_key": "name",
  "y_key": "value",
  "show_change": true
}
```

## 3. 创建 Recharts 图表组件

在前端项目中创建图表组件文件，例如 `src/components/charts/RechartsComponents.tsx`：

```tsx
import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// 颜色配置
const CHART_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6'];

interface ChartData {
  chart_type?: string;
  title: string;
  data: any[];
  x_key?: string;
  y_key?: string;
  y_keys?: string[];
  y_labels?: string[];
  colors?: string[];
  value_key?: string;
  label_key?: string;
  color?: string;
  show_change?: boolean;
}

// 通用样式
const chartContainerStyle: React.CSSProperties = {
  marginTop: 16,
};

const titleStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: '#1e293b',
  marginBottom: 12,
  display: 'flex',
  alignItems: 'center',
  gap: 8,
};

const chartWrapperStyle: React.CSSProperties = {
  background: 'linear-gradient(180deg, #fafbfc 0%, #f1f5f9 100%)',
  borderRadius: 12,
  padding: '16px 12px 8px 0',
  boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
};

// Tooltip 样式配置
const tooltipStyle = {
  contentStyle: {
    background: 'rgba(255, 255, 255, 0.96)',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
  },
  labelStyle: { fontWeight: 600, color: '#1e293b', marginBottom: 4 },
  itemStyle: { fontSize: 12, padding: '2px 0' },
};

/**
 * 折线/面积图组件
 */
export const RechartsLineChart: React.FC<{ data: ChartData }> = ({ data }) => {
  const chartData = data.data || [];
  if (chartData.length === 0) return null;

  const xKey = data.x_key || 'date';
  const yKeys = data.y_keys || [data.y_key || 'value'];
  const colors = data.colors || CHART_COLORS;
  const yLabels = data.y_labels || yKeys;

  return (
    <div style={chartContainerStyle}>
      <div style={titleStyle}>
        <span
          style={{
            width: 4,
            height: 16,
            background: `linear-gradient(180deg, ${colors[0]} 0%, ${colors[0]}80 100%)`,
            borderRadius: 2,
          }}
        />
        {data.title}
      </div>
      <div style={chartWrapperStyle}>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              {yKeys.map((key, i) => (
                <linearGradient key={`gradient-${key}`} id={`color-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors[i % colors.length]} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={colors[i % colors.length]} stopOpacity={0.05} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey={xKey}
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#64748b', fontSize: 11 }}
              dy={8}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              width={45}
              tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value)}
            />
            <Tooltip {...tooltipStyle} />
            {yKeys.map((key, i) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                name={yLabels[i]}
                stroke={colors[i % colors.length]}
                strokeWidth={2.5}
                fill={`url(#color-${key})`}
                dot={{ r: 4, fill: '#fff', stroke: colors[i % colors.length], strokeWidth: 2 }}
                activeDot={{ r: 6, fill: colors[i % colors.length], stroke: '#fff', strokeWidth: 2 }}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {/* 图例 */}
      <div
        style={{
          display: 'flex',
          gap: 20,
          marginTop: 12,
          justifyContent: 'center',
          padding: '8px 12px',
          background: '#f8fafc',
          borderRadius: 8,
        }}
      >
        {yKeys.map((key: string, i: number) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span
              style={{
                width: 20,
                height: 4,
                background: `linear-gradient(90deg, ${colors[i % colors.length]} 0%, ${colors[i % colors.length]}80 100%)`,
                borderRadius: 2,
                boxShadow: `0 0 6px ${colors[i % colors.length]}40`,
              }}
            />
            <span style={{ color: '#475569', fontWeight: 500 }}>{yLabels[i]}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 饼图/环形图组件
 */
export const RechartsPieChart: React.FC<{ data: ChartData }> = ({ data }) => {
  const chartData = data.data || [];
  if (chartData.length === 0) return null;

  const valueKey = data.value_key || 'value';
  const labelKey = data.label_key || 'name';
  const colors = data.colors || CHART_COLORS;

  // 转换数据格式
  const pieData = chartData.map((d: any, i: number) => ({
    name: d[labelKey],
    value: d[valueKey] || 0,
    icon: d.icon,
    fill: d.color || colors[i % colors.length],
  }));

  const total = pieData.reduce((sum: number, d: any) => sum + d.value, 0);

  // 自定义标签渲染
  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null;

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={11}
        fontWeight={600}
        style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div style={chartContainerStyle}>
      <div style={titleStyle}>
        <span
          style={{
            width: 4,
            height: 16,
            background: `linear-gradient(180deg, ${colors[0]} 0%, ${colors[1]} 100%)`,
            borderRadius: 2,
          }}
        />
        {data.title}
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          padding: '16px 20px',
          background: 'linear-gradient(135deg, #fafbfc 0%, #f1f5f9 100%)',
          borderRadius: 12,
          boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
        }}
      >
        <div style={{ width: 160, height: 160 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderCustomLabel}
                outerRadius={70}
                innerRadius={40}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
              >
                {pieData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.fill}
                    style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))' }}
                  />
                ))}
              </Pie>
              <Tooltip
                {...tooltipStyle}
                formatter={(value: number) => [value.toLocaleString(), '数值']}
              />
              {/* 中心总数 - 使用 SVG text 元素 */}
            </PieChart>
          </ResponsiveContainer>
          {/* 中心文字覆盖层 */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
              pointerEvents: 'none',
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#1e293b' }}>
              {total.toLocaleString()}
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>总计</div>
          </div>
        </div>

        {/* 图例 */}
        <div style={{ display: 'grid', gap: 8, flex: 1 }}>
          {pieData.map((item, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                background: '#fff',
                borderRadius: 8,
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                cursor: 'pointer',
              }}
            >
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 4,
                  background: item.fill,
                  boxShadow: `0 2px 4px ${item.fill}40`,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  color: '#475569',
                  fontSize: 12,
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                {item.icon ? <span>{item.icon}</span> : null}
                {item.name}
              </span>
              <span
                style={{
                  color: '#1e293b',
                  fontWeight: 600,
                  fontSize: 12,
                  background: `${item.fill}15`,
                  padding: '2px 8px',
                  borderRadius: 4,
                }}
              >
                {total > 0 ? ((item.value / total) * 100).toFixed(1) : 0}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * 柱状图组件（横向）
 */
export const RechartsBarChart: React.FC<{ data: ChartData }> = ({ data }) => {
  const chartData = data.data || [];
  if (chartData.length === 0) return null;

  const xKey = data.x_key || 'name';
  const yKey = data.y_key || 'value';
  const baseColor = data.color || '#6366f1';
  const colors = data.colors || CHART_COLORS;

  // 准备数据
  const barData = chartData.map((d: any, i: number) => ({
    ...d,
    fill: d.color || colors[i % colors.length],
  }));

  return (
    <div style={chartContainerStyle}>
      <div style={titleStyle}>
        <span
          style={{
            width: 4,
            height: 16,
            background: `linear-gradient(180deg, ${baseColor} 0%, ${baseColor}80 100%)`,
            borderRadius: 2,
          }}
        />
        {data.title}
      </div>
      <div style={chartWrapperStyle}>
        <ResponsiveContainer width="100%" height={Math.max(200, barData.length * 50)}>
          <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
            <defs>
              {barData.map((entry, index) => (
                <linearGradient
                  key={`bar-gradient-${index}`}
                  id={`bar-gradient-${index}`}
                  x1="0"
                  y1="0"
                  x2="1"
                  y2="0"
                >
                  <stop offset="0%" stopColor={entry.fill} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={entry.fill} stopOpacity={0.6} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={true} vertical={false} />
            <XAxis
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value)}
            />
            <YAxis
              dataKey={xKey}
              type="category"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#475569', fontSize: 12 }}
              width={75}
            />
            <Tooltip
              {...tooltipStyle}
              formatter={(value: number) => [value.toLocaleString(), '数值']}
            />
            <Bar dataKey={yKey} radius={[0, 6, 6, 0]} barSize={24}>
              {barData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={`url(#bar-gradient-${index})`} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

/**
 * 根据 chart_type 自动选择图表组件
 */
export const AutoChart: React.FC<{ data: ChartData }> = ({ data }) => {
  switch (data.chart_type) {
    case 'line':
      return <RechartsLineChart data={data} />;
    case 'pie':
      return <RechartsPieChart data={data} />;
    case 'bar':
      return <RechartsBarChart data={data} />;
    default:
      return <RechartsLineChart data={data} />;
  }
};

export default { RechartsLineChart, RechartsPieChart, RechartsBarChart, AutoChart };
```

## 4. 在前端项目中集成

### 方式一：覆盖后端组件（推荐）

如果 `agent-chat-ui` 支持自定义组件覆盖，在组件注册处添加：

```tsx
import { RechartsLineChart, RechartsPieChart, RechartsBarChart } from './components/charts/RechartsComponents';

// 在组件注册配置中
const customComponents = {
  LineChart: RechartsLineChart,
  PieChart: RechartsPieChart,
  BarChart: RechartsBarChart,
};
```

### 方式二：修改 SiteReportCard 渲染

如果需要直接修改 `SiteReportCard` 组件，找到图表渲染部分并替换：

```tsx
// 原来的
{charts.daily_visits ? <LineChart data={charts.daily_visits} /> : null}

// 改为
{charts.daily_visits ? <RechartsLineChart data={charts.daily_visits} /> : null}
```

## 5. 样式增强（可选）

添加 CSS 动画效果：

```css
/* 在全局样式文件中添加 */
@keyframes chart-fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.recharts-wrapper {
  animation: chart-fade-in 0.4s ease-out;
}

.recharts-tooltip-wrapper {
  z-index: 100;
}

.recharts-default-tooltip {
  background: rgba(255, 255, 255, 0.96) !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
  padding: 10px 14px !important;
}

.recharts-tooltip-label {
  font-weight: 600 !important;
  color: #1e293b !important;
  margin-bottom: 6px !important;
}

.recharts-tooltip-item {
  font-size: 12px !important;
  padding: 2px 0 !important;
}

.recharts-legend-item-text {
  font-size: 12px !important;
  color: #475569 !important;
}
```

## 6. 注意事项

1. **数据格式兼容**：确保后端传递的图表数据格式与上述 `ChartData` 接口一致

2. **响应式设计**：`ResponsiveContainer` 组件会自动适应父容器宽度，确保父容器有明确的宽度

3. **颜色一致性**：前后端使用相同的颜色配置，保持视觉一致性

4. **性能优化**：对于大数据量，考虑使用虚拟化或数据采样

5. **TypeScript 支持**：Recharts 自带类型定义，无需额外安装 @types 包

## 7. 效果预览

集成后，图表将具有以下特性：

- ✅ 平滑的动画效果
- ✅ 交互式 Tooltip
- ✅ 响应式布局
- ✅ 渐变填充和阴影效果
- ✅ 美观的图例展示
- ✅ 支持数据点悬停高亮

## 8. 故障排除

### 问题：图表不显示
- 检查父容器是否有明确的宽高
- 确认 `ResponsiveContainer` 的 `width` 和 `height` 设置正确

### 问题：样式冲突
- 检查是否有全局 CSS 覆盖了 Recharts 的样式
- 使用更具体的 CSS 选择器或 CSS Modules

### 问题：数据格式错误
- 使用浏览器开发者工具检查传入的 props
- 确认 `data.data` 是数组且非空

